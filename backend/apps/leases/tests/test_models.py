import datetime

from django.db import IntegrityError
from django.test import TestCase

from apps.leases.models import Lease, LeaseChunk, LeaseQuery, LeaseTerm, Property
from apps.users.models import User


class PropertyModelTests(TestCase):
    def test_create_property(self):
        prop = Property.objects.create(address="1 Test St", property_type=Property.TYPE_OFFICE)
        self.assertEqual(str(prop), "1 Test St")


class LeaseModelTests(TestCase):
    def setUp(self):
        self.property = Property.objects.create(address="1 Test St", property_type="office")

    def test_create_lease_defaults_to_uploaded(self):
        lease = Lease.objects.create(
            property=self.property,
            tenant_name="Acme",
            landlord_name="Landlord Co",
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
        )
        self.assertEqual(lease.status, Lease.STATUS_UPLOADED)

    def test_lease_term_and_chunk_relations(self):
        lease = Lease.objects.create(
            property=self.property,
            tenant_name="Acme",
            landlord_name="Landlord Co",
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
        )
        LeaseTerm.objects.create(
            lease=lease, term_type="rent", extracted_value="$1000/mo", source_page=1
        )
        LeaseChunk.objects.create(
            lease=lease, chunk_text="some text", chunk_index=0, search_doc_id="x1"
        )
        self.assertEqual(lease.terms.count(), 1)
        self.assertEqual(lease.chunks.count(), 1)

    def test_unique_chunk_index_per_lease(self):
        lease = Lease.objects.create(
            property=self.property,
            tenant_name="Acme",
            landlord_name="Landlord Co",
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
        )
        LeaseChunk.objects.create(
            lease=lease, chunk_text="a", chunk_index=0, search_doc_id="d1"
        )
        with self.assertRaises(IntegrityError):
            LeaseChunk.objects.create(
                lease=lease, chunk_text="b", chunk_index=0, search_doc_id="d2"
            )


class LeaseQueryModelTests(TestCase):
    def test_create_lease_query(self):
        prop = Property.objects.create(address="1 Test St", property_type="office")
        lease = Lease.objects.create(
            property=prop,
            tenant_name="Acme",
            landlord_name="Landlord Co",
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
        )
        user = User.objects.create_user(email="asker@example.com", password="StrongPass123!")
        query = LeaseQuery.objects.create(
            asked_by=user,
            lease=lease,
            question_text="What is the rent?",
            answer_text="It is $1000/mo",
            retrieved_chunk_ids=["lease-1-chunk-0"],
        )
        self.assertEqual(query.retrieved_chunk_ids, ["lease-1-chunk-0"])
