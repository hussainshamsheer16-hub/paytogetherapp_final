from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.expeness.models import Expense
from apps.reports.models import SettlementPayment
from apps.tour.models import Tour, TourMember


@override_settings(STRIPE_SECRET_KEY="sk_test_123")
class StripePaymentTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            email="stripe-owner@example.com",
            username="stripe-owner",
            password="password123",
        )
        self.member = user_model.objects.create_user(
            email="stripe-member@example.com",
            username="stripe-member",
            password="password123",
        )
        self.other_user = user_model.objects.create_user(
            email="stripe-other@example.com",
            username="stripe-other",
            password="password123",
        )
        self.tour = Tour.objects.create(
            created_by=self.owner,
            title="Stripe Tour",
            destination="Test Destination",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 3),
        )
        TourMember.objects.create(tour=self.tour, user=self.member)
        Expense.objects.create(
            tour=self.tour,
            paid_by=self.owner,
            added_by=self.owner,
            amount="100.00",
            category="other",
        )
        self.url = "/api/payments/create-checkout-session/"

    def _checkout_payload(self, **extra):
        payload = {"tour_id": self.tour.id, "to_id": self.owner.id}
        payload.update(extra)
        return payload

    @patch("apps.payments.views.stripe.checkout.Session.create")
    def test_member_can_create_checkout_without_trusting_client_amount(self, create):
        create.return_value = SimpleNamespace(id="cs_test_123", url="https://checkout.test/123")
        self.client.force_authenticate(user=self.member)

        response = self.client.post(
            self.url,
            self._checkout_payload(amount="0.01"),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"success": True, "checkout_url": "https://checkout.test/123"})
        self.assertEqual(create.call_args.kwargs["payment_method_types"], ["card"])
        self.assertEqual(create.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"], 5000)
        payment = SettlementPayment.objects.get(stripe_checkout_session_id="cs_test_123")
        self.assertEqual(payment.amount, Decimal("50.00"))
        self.assertEqual(payment.status, "pending")

    @patch("apps.payments.views.stripe.checkout.Session.create")
    def test_user_cannot_create_checkout_for_another_tour(self, create):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            self.url,
            self._checkout_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        create.assert_not_called()

    def test_invalid_and_paid_orders_are_rejected(self):
        self.client.force_authenticate(user=self.member)
        invalid = self.client.post(self.url, {"tour_id": "invalid"}, format="json")
        self.assertEqual(invalid.status_code, 400)

        payment = SettlementPayment.objects.create(
            tour=self.tour,
            payer=self.member,
            recipient=self.owner,
            amount="50.00",
            payment_method="card",
            status="paid",
            currency="usd",
        )
        with patch("apps.payments.views.stripe.checkout.Session.create") as create:
            paid = self.client.post(self.url, self._checkout_payload(), format="json")
        self.assertEqual(paid.status_code, 409)
        create.assert_not_called()
        self.assertEqual(payment.status, "paid")

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_invalid_webhook_signature_is_rejected(self, construct_event):
        import stripe

        construct_event.side_effect = stripe.error.SignatureVerificationError("bad", "sig")
        response = self.client.post(
            "/api/payments/stripe/webhook/",
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid",
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_valid_webhook_marks_paid_and_is_idempotent(self, construct_event):
        payment = SettlementPayment.objects.create(
            tour=self.tour,
            payer=self.member,
            recipient=self.owner,
            amount="50.00",
            payment_method="card",
            status="pending",
            currency="usd",
            stripe_checkout_session_id="cs_test_123",
        )
        event = {
            "type": "checkout.session.completed",
            "data": {"object": {
                "id": "cs_test_123",
                "object": "checkout.session",
                "payment_status": "paid",
                "amount_total": 5000,
                "currency": "usd",
                "payment_intent": "pi_test_123",
                "metadata": {
                    "payment_id": str(payment.id),
                    "tour_id": str(self.tour.id),
                    "user_id": str(self.member.id),
                },
            }},
        }
        construct_event.return_value = event

        first = self.client.post(
            "/api/payments/stripe/webhook/",
            data=b"signed",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )
        second = self.client.post(
            "/api/payments/stripe/webhook/",
            data=b"signed",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )
        payment.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(payment.status, "paid")
        self.assertEqual(payment.stripe_payment_intent_id, "pi_test_123")
        self.assertIsNotNone(payment.paid_at)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    @patch("apps.payments.views.stripe.Webhook.construct_event")
    def test_failed_webhook_does_not_mark_paid(self, construct_event):
        payment = SettlementPayment.objects.create(
            tour=self.tour,
            payer=self.member,
            recipient=self.owner,
            amount="50.00",
            payment_method="card",
            status="pending",
            currency="usd",
            stripe_checkout_session_id="cs_test_failed",
        )
        construct_event.return_value = {
            "type": "checkout.session.expired",
            "data": {"object": {
                "id": "cs_test_failed",
                "object": "checkout.session",
                "status": "expired",
                "metadata": {"payment_id": str(payment.id)},
            }},
        }
        response = self.client.post(
            "/api/payments/stripe/webhook/",
            data=b"signed",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="valid",
        )
        payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment.status, "cancelled")
        self.assertNotEqual(payment.status, "paid")

    def test_success_page_does_not_mark_payment_paid(self):
        payment = SettlementPayment.objects.create(
            tour=self.tour,
            payer=self.member,
            recipient=self.owner,
            amount="50.00",
            payment_method="card",
            status="pending",
            currency="usd",
            stripe_checkout_session_id="cs_success_page",
        )
        self.client.force_authenticate(user=self.member)
        response = self.client.get(
            "/payments/success/?session_id=cs_success_page"
        )
        payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment.status, "pending")
