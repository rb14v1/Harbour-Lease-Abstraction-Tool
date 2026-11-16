"""
Vector/hybrid search abstraction (wraps azure-search-documents).

Real path: when settings.AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY are both
set, calls a real Azure AI Search index via SearchClient. Postgres itself
never stores vectors -- this module is the only place embeddings live.

Stub path: when unconfigured (the default in dev/test), keeps a process-local
in-memory list of {id, vector, payload} per index name and implements
cosine-similarity top-k search in plain Python. This mirrors how sibling apps
use an in-memory vector store (e.g. Qdrant ":memory:" mode) for tests -- it
only needs to survive a single test/process run, no persistence required.
"""
import math
from django.conf import settings

# Process-local fallback store: {index_name: [{"id":..., "vector":[...], "payload": {...}}, ...]}
_MEMORY_STORE: dict[str, list[dict]] = {}


def _is_real():
    return bool(settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY)


def _index_client(index_name: str):
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential

    return SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY),
    )


def reset_index(index_name: str) -> None:
    """Test helper: clears the in-memory fallback store for an index."""
    _MEMORY_STORE.pop(index_name, None)


def upsert_chunks(index_name: str, items: list[dict]) -> None:
    """
    Upserts `items`, each a {"id": str, "vector": list[float], "payload": dict}.
    """
    if _is_real():
        client = _index_client(index_name)
        docs = []
        for item in items:
            doc = {"id": item["id"], "vector": item["vector"]}
            doc.update(item.get("payload", {}))
            docs.append(doc)
        client.merge_or_upload_documents(documents=docs)
        return

    bucket = _MEMORY_STORE.setdefault(index_name, [])
    existing_ids = {entry["id"]: pos for pos, entry in enumerate(bucket)}
    for item in items:
        record = {
            "id": item["id"],
            "vector": item["vector"],
            "payload": item.get("payload", {}),
        }
        if item["id"] in existing_ids:
            bucket[existing_ids[item["id"]]] = record
        else:
            bucket.append(record)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search(
    index_name: str,
    query_vector: list[float],
    top_k: int = 5,
    filter_fn=None,
) -> list[dict]:
    """
    Returns up to `top_k` {"id", "score", "payload"} dicts ranked by cosine
    similarity to `query_vector`. `filter_fn(payload) -> bool`, if given,
    restricts which payloads are considered (e.g. scoping to one lease_id).
    """
    if _is_real():
        client = _index_client(index_name)
        results = client.search(
            search_text=None,
            vector_queries=[
                {
                    "vector": query_vector,
                    "k_nearest_neighbors": top_k,
                    "fields": "vector",
                    "kind": "vector",
                }
            ],
        )
        out = []
        for r in results:
            payload = {k: v for k, v in r.items() if not k.startswith("@")}
            score = r.get("@search.score", 0.0)
            doc_id = payload.pop("id", None)
            if filter_fn and not filter_fn(payload):
                continue
            out.append({"id": doc_id, "score": score, "payload": payload})
        return out[:top_k]

    bucket = _MEMORY_STORE.get(index_name, [])
    scored = []
    for entry in bucket:
        if filter_fn and not filter_fn(entry["payload"]):
            continue
        score = _cosine_similarity(query_vector, entry["vector"])
        scored.append({"id": entry["id"], "score": score, "payload": entry["payload"]})
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top_k]
