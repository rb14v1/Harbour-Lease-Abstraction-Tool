from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class UserModelTests(TestCase):
    def test_create_user_hashes_password_and_defaults_role(self):
        user = User.objects.create_user(email="jane@example.com", password="StrongPass123!")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(user.role, User.ROLE_PROPERTY_MANAGER)
        self.assertFalse(user.is_admin)

    def test_create_superuser_is_admin(self):
        user = User.objects.create_superuser(email="root@example.com", password="StrongPass123!")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, User.ROLE_ADMIN)
        self.assertTrue(user.is_admin)

    def test_email_is_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertNotIn("username", [f.name for f in User._meta.get_fields()])


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_returns_tokens(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "newuser@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_and_refresh(self):
        User.objects.create_user(email="loginuser@example.com", password="StrongPass123!")
        login = self.client.post(
            "/api/auth/login/",
            {"email": "loginuser@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)

        refresh = self.client.post(
            "/api/auth/refresh/", {"refresh": login.data["refresh"]}, format="json"
        )
        self.assertEqual(refresh.status_code, 200)
        self.assertIn("access", refresh.data)

    def test_me_requires_auth(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_me_returns_current_user(self):
        user = User.objects.create_user(email="me@example.com", password="StrongPass123!")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "me@example.com")
