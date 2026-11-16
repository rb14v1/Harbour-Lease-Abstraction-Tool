"""
Business logic for the lease processing & question-answering pipeline.

Pipeline (all through the dual-path stub/real modules in apps.common):

1. process_lease(lease):
   download raw bytes from blob_store -> document_intelligence extracts
   full text + LeaseTerm rows -> text is chunked into LeaseChunk rows ->
   each chunk is embedded via ai.embed_text -> chunks are upserted into
   search_store under index "lease_chunks" (payload carries lease_id) ->
   lease.status becomes "processed".

2. ask_question(lease, user, question_text):
   embeds the question -> search_store.search top-k chunks filtered to this
   lease -> ai.chat_completion synthesizes an answer citing which chunks/terms
   were used -> a LeaseQuery row is saved with the retrieved chunk ids.
"""
from django.conf import settings

from apps.common import ai, blob_store, document_intelligence, search_store

from .models import Lease, LeaseChunk, LeaseQuery, LeaseTerm

SEARCH_INDEX = "lease_chunks"
CHUNK_SIZE_CHARS = 500


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> list[str]:
    """Splits text into roughly chunk_size-character chunks on paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > chunk_size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def process_lease(lease: Lease) -> Lease:
    """Runs the full extract -> chunk -> embed -> index pipeline for one lease."""
    lease.status = Lease.STATUS_PROCESSING
    lease.save(update_fields=["status"])

    raw_bytes = blob_store.download_document(lease.blob_path)

    full_text = document_intelligence.extract_text(raw_bytes)
    extracted_terms = document_intelligence.extract_lease_terms(raw_bytes)

    lease.terms.all().delete()
    LeaseTerm.objects.bulk_create(
        [
            LeaseTerm(
                lease=lease,
                term_type=t["term_type"],
                extracted_value=t["extracted_value"],
                source_page=t["source_page"],
            )
            for t in extracted_terms
        ]
    )

    lease.chunks.all().delete()
    chunks = chunk_text(full_text)
    search_items = []
    chunk_objs = []
    for idx, chunk in enumerate(chunks):
        search_doc_id = f"lease-{lease.id}-chunk-{idx}"
        chunk_objs.append(
            LeaseChunk(
                lease=lease,
                chunk_text=chunk,
                chunk_index=idx,
                search_doc_id=search_doc_id,
            )
        )
        vector = ai.embed_text(chunk)
        search_items.append(
            {
                "id": search_doc_id,
                "vector": vector,
                "payload": {
                    "lease_id": lease.id,
                    "chunk_index": idx,
                    "chunk_text": chunk,
                },
            }
        )

    LeaseChunk.objects.bulk_create(chunk_objs)
    if search_items:
        search_store.upsert_chunks(SEARCH_INDEX, search_items)

    lease.status = Lease.STATUS_PROCESSED
    lease.save(update_fields=["status"])
    return lease


def ask_question(lease: Lease, user, question_text: str) -> LeaseQuery:
    """Embeds the question, retrieves top chunks for this lease, and synthesizes an answer."""
    query_vector = ai.embed_text(question_text)

    def _scoped_to_lease(payload):
        return payload.get("lease_id") == lease.id

    results = search_store.search(
        SEARCH_INDEX, query_vector, top_k=5, filter_fn=_scoped_to_lease
    )

    terms = list(lease.terms.all())
    context_lines = []
    for r in results:
        payload = r["payload"]
        context_lines.append(
            f"[chunk {payload.get('chunk_index')}] {payload.get('chunk_text')}"
        )
    for t in terms:
        context_lines.append(
            f"[term:{t.term_type} p.{t.source_page}] {t.extracted_value}"
        )
    context = "\n".join(context_lines) if context_lines else "(no lease context available)"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a lease abstraction assistant. Answer the question using "
                "only the provided lease context, and cite which chunks or terms "
                "you used."
            ),
        },
        {
            "role": "user",
            "content": f"Lease context:\n{context}\n\nQuestion: {question_text}",
        },
    ]
    answer_text = ai.chat_completion(messages)

    retrieved_chunk_ids = [r["id"] for r in results]

    return LeaseQuery.objects.create(
        asked_by=user,
        lease=lease,
        question_text=question_text,
        answer_text=answer_text,
        retrieved_chunk_ids=retrieved_chunk_ids,
    )
