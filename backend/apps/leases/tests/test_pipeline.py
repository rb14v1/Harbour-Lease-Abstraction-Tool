"""
True end-to-end pipeline test, entirely through stub mode:
upload -> extract -> chunk/embed -> index -> search -> AI answer.
"""
import datetime

from django.test import TestCase

from apps.common import blob_store, search_store
from apps.leases import services
from apps.leases.models import Lease, LeaseChunk, LeaseQuery, LeaseTerm, Property
from apps.users.models import User

LEASE_TEXT = (
    "LEASE AGREEMENT\n\n"
    "RENT. Tenant shall pay $3500.00 per month in base rent to the landlord.\n\n"
    "RENEWAL. Tenant may renew this lease for additional terms upon written notice.\n\n"
    "TERMINATION. Either party may terminate this lease with 90 days written notice.\n\n"
    "MAINTENANCE. Landlord is responsible for maintenance and structural repairs."
)


class EndToEndPipelineTests(TestCase):
    def setUp(self):
        search_store.reset_index(services.SEARCH_INDEX)
        self.user = User.objects.create_user(
            email="pipeline@test.com", password="StrongPass123!"
        )
        self.property = Property.objects.create(address="500 Pipeline Ave", property_type="office")

    def test_full_pipeline_upload_through_answer(self):
        # 1. Upload: store document via blob_store, create Lease(status=uploaded).
        blob_path = blob_store.upload_document(
            LEASE_TEXT.encode("utf-8"), "lease-documents", "pipeline_lease.txt"
        )
        lease = Lease.objects.create(
            property=self.property,
            tenant_name="Pipeline Tenant",
            landlord_name="Pipeline Landlord",
            blob_path=blob_path,
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2026, 1, 1),
            status=Lease.STATUS_UPLOADED,
        )
        self.assertEqual(lease.status, Lease.STATUS_UPLOADED)

        # 2. Process: extract -> chunk/embed -> index -> processed.
        lease = services.process_lease(lease)
        self.assertEqual(lease.status, Lease.STATUS_PROCESSED)

        terms = list(LeaseTerm.objects.filter(lease=lease))
        self.assertGreater(len(terms), 0)
        term_types = {t.term_type for t in terms}
        self.assertTrue(term_types.issubset({"rent", "renewal", "termination", "maintenance"}))

        chunks = list(LeaseChunk.objects.filter(lease=lease).order_by("chunk_index"))
        self.assertGreater(len(chunks), 0)

        # Confirm chunks really landed in the search index payload-scoped to this lease.
        search_results = search_store.search(
            services.SEARCH_INDEX,
            [0.0] * 1536,
            top_k=100,
            filter_fn=lambda p: p.get("lease_id") == lease.id,
        )
        self.assertEqual(len(search_results), len(chunks))

        # 3. Ask a question: embed -> search top-k (scoped to lease) -> chat -> LeaseQuery saved.
        query = services.ask_question(lease, self.user, "What is the monthly rent?")
        self.assertIsInstance(query, LeaseQuery)
        self.assertEqual(query.lease_id, lease.id)
        self.assertEqual(query.asked_by_id, self.user.id)
        self.assertTrue(query.answer_text)
        self.assertGreater(len(query.retrieved_chunk_ids), 0)
        for chunk_id in query.retrieved_chunk_ids:
            self.assertTrue(chunk_id.startswith(f"lease-{lease.id}-chunk-"))

        self.assertEqual(LeaseQuery.objects.filter(lease=lease).count(), 1)

    def test_pipeline_scopes_search_to_correct_lease(self):
        blob_path_a = blob_store.upload_document(
            LEASE_TEXT.encode("utf-8"), "lease-documents", "lease_a.txt"
        )
        blob_path_b = blob_store.upload_document(
            "RENT. Tenant pays $9999.00 per month for a different unit.".encode("utf-8"),
            "lease-documents",
            "lease_b.txt",
        )
        lease_a = services.process_lease(
            Lease.objects.create(
                property=self.property,
                tenant_name="Tenant A",
                landlord_name="Landlord A",
                blob_path=blob_path_a,
                start_date=datetime.date(2024, 1, 1),
                end_date=datetime.date(2026, 1, 1),
            )
        )
        lease_b = services.process_lease(
            Lease.objects.create(
                property=self.property,
                tenant_name="Tenant B",
                landlord_name="Landlord B",
                blob_path=blob_path_b,
                start_date=datetime.date(2024, 1, 1),
                end_date=datetime.date(2026, 1, 1),
            )
        )

        query = services.ask_question(lease_b, self.user, "What is the rent?")
        for chunk_id in query.retrieved_chunk_ids:
            self.assertTrue(chunk_id.startswith(f"lease-{lease_b.id}-chunk-"))
            self.assertFalse(chunk_id.startswith(f"lease-{lease_a.id}-chunk-"))
