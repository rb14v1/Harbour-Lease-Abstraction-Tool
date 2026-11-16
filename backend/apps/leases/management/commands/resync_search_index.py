"""
Rebuilds the search_store "lease_chunks" index from the LeaseChunk table.

The in-memory search_store fallback used in stub mode is process-local and
does not persist across server restarts (the DB rows are the durable
source of truth). This command re-embeds and re-upserts every existing
LeaseChunk so that question-answering works immediately after a fresh
server start, without needing to re-run the full extraction pipeline.
Safe to run anytime; it is idempotent (upsert by search_doc_id).
"""
from django.core.management.base import BaseCommand

from apps.common import ai, search_store
from apps.leases.models import LeaseChunk
from apps.leases.services import SEARCH_INDEX


class Command(BaseCommand):
    help = "Rebuilds the in-memory/real search index from existing LeaseChunk rows."

    def handle(self, *args, **options):
        items = []
        for chunk in LeaseChunk.objects.select_related("lease").all():
            vector = ai.embed_text(chunk.chunk_text)
            items.append(
                {
                    "id": chunk.search_doc_id,
                    "vector": vector,
                    "payload": {
                        "lease_id": chunk.lease_id,
                        "chunk_index": chunk.chunk_index,
                        "chunk_text": chunk.chunk_text,
                    },
                }
            )
        if items:
            search_store.upsert_chunks(SEARCH_INDEX, items)
        self.stdout.write(self.style.SUCCESS(f"Resynced {len(items)} chunks into '{SEARCH_INDEX}'."))
