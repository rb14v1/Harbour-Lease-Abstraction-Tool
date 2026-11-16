import datetime
import io

from django.test import TestCase
from rest_framework.test import APIClient

from apps.leases.models import Lease, Property
from apps.users.models import User


class BaseApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pm_user = User.objects.create_user(
            email="pm@test.com", password="StrongPass123!", role=User.ROLE_PROPERTY_MANAGER
        )
        self.admin_user = User.objects.create_user(
            email="admin@test.com", password="StrongPass123!", role=User.ROLE_ADMIN
        )
        self.property = Property.objects.create(address="1 Test St", property_type="office")
        self.lease = Lease.objects.create(
            property=self.property,
            tenant_name="Acme",
            landlord_name="Landlord Co",
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
        )


class PropertyApiTests(BaseApiTestCase):
    def test_list_requires_auth(self):
        response = self.client.get("/api/properties/")
        self.assertEqual(response.status_code, 401)

    def test_property_manager_can_list_and_create(self):
        self.client.force_authenticate(user=self.pm_user)
        response = self.client.get("/api/properties/")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/properties/", {"address": "2 New St", "property_type": "retail"}
        )
        self.assertEqual(response.status_code, 201)

    def test_property_manager_cannot_delete(self):
        self.client.force_authenticate(user=self.pm_user)
        response = self.client.delete(f"/api/properties/{self.property.id}/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_delete(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f"/api/properties/{self.property.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Property.objects.filter(id=self.property.id).exists())


class LeaseApiTests(BaseApiTestCase):
    def test_upload_lease_creates_record(self):
        self.client.force_authenticate(user=self.pm_user)
        upload = io.BytesIO(b"RENT. Pay $1000.\n\nTERMINATION. 30 days notice.")
        upload.name = "lease.txt"
        response = self.client.post(
            "/api/leases/",
            {
                "property": self.property.id,
                "tenant_name": "New Tenant",
                "landlord_name": "New Landlord",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "file": upload,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "uploaded")
        self.assertTrue(response.data["blob_path"].startswith("stub://"))

    def test_process_lease_populates_terms_and_marks_processed(self):
        self.lease.blob_path = self._seed_blob()
        self.lease.save()
        self.client.force_authenticate(user=self.pm_user)
        response = self.client.post(f"/api/leases/{self.lease.id}/process/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "processed")

        terms_response = self.client.get(f"/api/leases/{self.lease.id}/terms/")
        self.assertEqual(terms_response.status_code, 200)
        self.assertGreater(len(terms_response.data), 0)

    def test_lease_manager_cannot_delete_but_admin_can(self):
        self.client.force_authenticate(user=self.pm_user)
        response = self.client.delete(f"/api/leases/{self.lease.id}/")
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f"/api/leases/{self.lease.id}/")
        self.assertEqual(response.status_code, 204)

    def _seed_blob(self):
        from apps.common import blob_store

        text = (
            "RENT. Tenant pays monthly rent.\n\n"
            "RENEWAL. Tenant may renew with written notice.\n\n"
            "TERMINATION. 60 days notice required.\n\n"
            "MAINTENANCE. Landlord handles repairs."
        )
        return blob_store.upload_document(text.encode("utf-8"), "lease-documents", "seed.txt")


class LeaseQueryApiTests(BaseApiTestCase):
    def test_ask_question_after_processing(self):
        from apps.common import blob_store

        text = "RENT. Tenant pays $2000 monthly.\n\nTERMINATION. 90 days notice required."
        self.lease.blob_path = blob_store.upload_document(
            text.encode("utf-8"), "lease-documents", "q.txt"
        )
        self.lease.save()

        self.client.force_authenticate(user=self.pm_user)
        process_response = self.client.post(f"/api/leases/{self.lease.id}/process/")
        self.assertEqual(process_response.status_code, 200)

        ask_response = self.client.post(
            f"/api/leases/{self.lease.id}/queries/",
            {"question_text": "What is the monthly rent?"},
            format="json",
        )
        self.assertEqual(ask_response.status_code, 201, ask_response.data)
        self.assertIn("answer_text", ask_response.data)
        self.assertIsInstance(ask_response.data["retrieved_chunk_ids"], list)

        history_response = self.client.get(f"/api/leases/{self.lease.id}/queries/")
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.data), 1)
