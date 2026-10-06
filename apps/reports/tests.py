from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.expeness.models import Expense
from apps.reports.models import Notification, SettlementPayment
from apps.tour.models import Tour, TourMember


class SettlementPaymentAPITests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.owner = user_model.objects.create_user(
			email="report-owner@example.com",
			username="report-owner",
			password="password123",
		)
		self.member = user_model.objects.create_user(
			email="report-member@example.com",
			username="report-member",
			password="password123",
		)
		self.tour = Tour.objects.create(
			created_by=self.owner,
			title="Report Tour",
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

	def test_unpaid_settlement_can_be_paid_with_cod(self):
		self.client.force_authenticate(user=self.member)
		report_url = f"/api/tours/{self.tour.id}/report/"
		payment_url = f"/api/tours/{self.tour.id}/settlements/pay/"

		report = self.client.get(report_url)
		self.assertEqual(report.status_code, 200)
		settlement = report.data["settlements"][0]
		self.assertEqual(settlement["status"], "unpaid")

		payment = self.client.post(
			payment_url,
			{
				"to_id": settlement["to_id"],
				"amount": settlement["amount"],
				"payment_method": "cod",
			},
			format="json",
		)
		self.assertEqual(payment.status_code, 200)
		self.assertEqual(payment.data["status"], "pending")

		pending_report = self.client.get(report_url)
		pending_settlement = pending_report.data["settlements"][0]
		self.assertEqual(pending_settlement["status"], "pending")

		self.client.force_authenticate(user=self.owner)
		approval = self.client.post(
			f"/api/tours/{self.tour.id}/settlements/{payment.data['id']}/approve/",
			{"decision": "received"},
			format="json",
		)
		self.assertEqual(approval.status_code, 200)
		self.assertEqual(approval.data["status"], "paid")

		updated_report = self.client.get(report_url)
		self.assertEqual(updated_report.data["settlements"][0]["status"], "paid")
		self.assertEqual(updated_report.data["settlements"][0]["payment_method"], "cod")

	def test_pending_payment_creates_notification_and_status_update_options(self):
		self.client.force_authenticate(user=self.member)
		report = self.client.get(f"/api/tours/{self.tour.id}/report/")
		settlement = report.data["settlements"][0]
		payment = self.client.post(
			f"/api/tours/{self.tour.id}/settlements/pay/",
			{"to_id": settlement["to_id"], "amount": settlement["amount"], "payment_method": "cod"},
			format="json",
		)
		self.assertEqual(payment.status_code, 200)
		self.assertTrue(Notification.objects.filter(user=self.owner, payment_id=payment.data["id"], title="Money received").exists())
		self.client.force_authenticate(user=self.owner)
		notification_response = self.client.get("/api/notifications/")
		payment_notification = next(item for item in notification_response.data["notifications"] if item["payment_id"] == payment.data["id"])
		self.assertTrue(payment_notification["can_approve"])
		self.client.post(f"/api/notifications/{payment_notification['id']}/read/")
		read_response = self.client.get("/api/notifications/")
		read_notification = next(item for item in read_response.data["notifications"] if item["payment_id"] == payment.data["id"])
		self.assertFalse(read_notification["can_approve"])
		response = self.client.post(
			f"/api/tours/{self.tour.id}/settlements/{payment.data['id']}/approve/",
			{"decision": "not_received"}, format="json",
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["status"], "not_received")
		self.assertTrue(Notification.objects.filter(user=self.member, payment_id=payment.data["id"], title="Payment not confirmed", message__contains="check this transaction again").exists())
		self.client.force_authenticate(user=self.member)
		retry = self.client.post(
			f"/api/tours/{self.tour.id}/settlements/pay/",
			{"to_id": settlement["to_id"], "amount": settlement["amount"], "payment_method": "cod"},
			format="json",
		)
		self.assertEqual(retry.status_code, 200)
		self.assertEqual(retry.data["status"], "pending")

	def test_raast_ids_create_pending_recipient_approval_and_then_paid(self):
		self.client.force_authenticate(user=self.member)
		response = self.client.post("/api/payments/raast/manual/", {
			"tour_id": self.tour.id, "to_id": self.owner.id,
			"sender_raast_id": "sender-raast", "recipient_raast_id": "receiver-raast",
		}, format="json")
		self.assertEqual(response.status_code, 200)
		payment = SettlementPayment.objects.get(pk=response.data["payment_id"])
		self.assertEqual(payment.status, "pending")
		self.assertEqual(payment.sender_raast_id, "sender-raast")
		self.assertIsNone(payment.paid_at)
		notification = Notification.objects.get(user=self.owner, payment=payment)
		self.assertIn("sender-raast", notification.message)
		self.assertIn("receiver-raast", notification.message)
		self.client.force_authenticate(user=self.owner)
		approval = self.client.post(f"/api/tours/{self.tour.id}/settlements/{payment.id}/approve/", {"decision": "received"}, format="json")
		payment.refresh_from_db()
		self.assertEqual(approval.status_code, 200)
		self.assertEqual(payment.status, "paid")
		self.assertIsNotNone(payment.paid_at)

	def test_raast_duplicate_request_is_idempotent_and_requires_both_ids(self):
		self.client.force_authenticate(user=self.member)
		url = "/api/payments/raast/manual/"
		payload = {"tour_id": self.tour.id, "to_id": self.owner.id, "sender_raast_id": "sender-raast", "recipient_raast_id": "receiver-raast"}
		missing_id = self.client.post(url, {**payload, "recipient_raast_id": ""}, format="json")
		self.assertEqual(missing_id.status_code, 400)
		first = self.client.post(url, payload, format="json")
		second = self.client.post(url, payload, format="json")
		self.assertEqual(first.status_code, 200)
		self.assertEqual(second.status_code, 200)
		self.assertEqual(first.data["payment_id"], second.data["payment_id"])
		self.assertEqual(SettlementPayment.objects.filter(tour=self.tour, payer=self.member).count(), 1)
		self.assertEqual(Notification.objects.filter(payment_id=first.data["payment_id"]).count(), 1)

	def test_raast_qr_links_to_the_valid_paytogether_settlement(self):
		self.client.force_authenticate(user=self.member)
		response = self.client.post(
			"/api/payments/raast/payment-link/",
			{"tour_id": self.tour.id, "to_id": self.owner.id},
			format="json",
		)
		self.assertEqual(response.status_code, 200)
		self.assertIn(f"/tours/{self.tour.id}/?pay_to={self.owner.id}&method=raast", response.data["payment_url"])
		self.assertTrue(response.data["qr_code"].startswith("data:image/svg+xml;base64,"))

# Create your tests here.
