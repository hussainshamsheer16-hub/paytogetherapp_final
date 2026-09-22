import json

from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from .models import User


class RegisterPageTests(TestCase):
    def test_register_page_renders_with_base_template(self):
        response = self.client.get(reverse("accounts:register-page"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PayTogether")
        self.assertContains(response, "Create your account")

    def test_register_page_uses_username_field(self):
        response = self.client.get(reverse("accounts:register-page"))

        self.assertContains(response, "Username")
        self.assertContains(response, "Full Name")
        self.assertContains(response, "Phone Number")

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="loginform"')
        self.assertContains(response, 'js/login.')

    def test_dashboard_page_renders(self):
        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'js/Dashboard.')

    def test_home_page_renders_base_template(self):
        response = self.client.get(reverse("accounts:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PayTogether")
        self.assertNotContains(response, 'js/Dashboard.js')


class AuthAPITests(TestCase):
    def test_register_api_creates_user(self):
        payload = {
            "full_name": "Test User",
            "username": "tester",
            "email": "tester@example.com",
            "phone_number": "1234567890",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
        }

        response = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])
        self.assertTrue(User.objects.filter(email="tester@example.com").exists())

    def test_register_api_rejects_duplicate_email(self):
        User.objects.create_user(
            email="existing@example.com", username="existing", password="StrongPass123"
        )
        payload = {
            "full_name": "Existing User",
            "username": "anotheruser",
            "email": "existing@example.com",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
        }

        response = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])

    def test_login_api_returns_tokens(self):
        user = User.objects.create_user(
            email="login@example.com",
            username="loginuser",
            password="StrongPass123",
        )

        response = self.client.post(
            reverse("accounts:login-api"),
            data=json.dumps({"email": user.email, "password": "StrongPass123"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("tokens", response.json())

    def test_profile_and_logout_api_require_and_accept_a_jwt(self):
        user = User.objects.create_user(
            email="profile@example.com",
            username="profileuser",
            first_name="Profile",
            last_name="User",
            password="StrongPass123",
        )
        authorization = f"Bearer {AccessToken.for_user(user)}"

        profile_response = self.client.get(
            reverse("accounts:profile"), HTTP_AUTHORIZATION=authorization
        )
        logout_response = self.client.post(
            reverse("accounts:logout-api"), HTTP_AUTHORIZATION=authorization
        )

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.json()["full_name"], "Profile User")
        self.assertEqual(logout_response.status_code, 200)
        self.assertTrue(logout_response.json()["success"])

    def test_profile_update_changes_email_and_returns_updated_profile(self):
        user = User.objects.create_user(
            email="before@example.com",
            username="profileupdate",
            password="StrongPass123",
        )
        authorization = f"Bearer {AccessToken.for_user(user)}"

        response = self.client.patch(
            reverse("accounts:profile-update"),
            data=json.dumps({"email": "after@example.com", "username": "updatedname"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=authorization,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["email"], "after@example.com")
        self.assertEqual(User.objects.get(pk=user.pk).email, "after@example.com")

    def test_password_change_succeeds_for_current_password(self):
        user = User.objects.create_user(
            email="passwordchange@example.com",
            username="passwordchange",
            password="StrongPass123",
        )
        authorization = f"Bearer {AccessToken.for_user(user)}"

        response = self.client.post(
            reverse("accounts:change-password"),
            data={"old_password": "StrongPass123", "new_password": "NewStrongPass123"},
            format="json",
            HTTP_AUTHORIZATION=authorization,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewStrongPass123"))

    def test_session_logout_redirects_to_login(self):
        user = User.objects.create_user(
            email="session@example.com", password="StrongPass123"
        )
        self.client.force_login(user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("accounts:login"))

    def test_logout_api_accepts_an_expired_or_missing_token(self):
        response = self.client.post(reverse("accounts:logout-api"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
