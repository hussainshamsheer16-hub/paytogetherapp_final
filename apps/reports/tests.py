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
			{
				"to_id": settlement["to_id"],
				"amount": settlement["amount"],
				"payment_method": "cod",
			},
			format="json",
		)
		self.assertEqual(payment.status_code, 200)
		self.assertTrue(
			Notification.objects.filter(
				user=self.owner,
				payment_id=payment.data["id"],
				title="Money received",
			).exists()
		)
		self.client.force_authenticate(user=self.owner)
		notification_response = self.client.get("/api/notifications/")
		payment_notification = next(
			item for item in notification_response.data["notifications"]
			if item["payment_id"] == payment.data["id"]
		)
		self.assertTrue(payment_notification["can_approve"])
		self.client.post(f"/api/notifications/{payment_notification['id']}/read/")
		read_response = self.client.get("/api/notifications/")
		read_notification = next(
			item for item in read_response.data["notifications"]
			if item["payment_id"] == payment.data["id"]
		)
		self.assertFalse(read_notification["can_approve"])

		response = self.client.post(
			f"/api/tours/{self.tour.id}/settlements/{payment.data['id']}/approve/",
			{"decision": "not_received"},
			format="json",
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["status"], "not_received")
		self.assertEqual(
			SettlementPayment.objects.get(id=payment.data["id"]).status,
			"not_received",
		)
		self.assertTrue(
			Notification.objects.filter(
				user=self.member,
				payment_id=payment.data["id"],
				title="Payment not confirmed",
				message__contains="check this transaction again",
			).exists()
		)

		self.client.force_authenticate(user=self.member)
		retry = self.client.post(
			f"/api/tours/{self.tour.id}/settlements/pay/",
			{
				"to_id": settlement["to_id"],
				"amount": settlement["amount"],
				"payment_method": "cod",
			},
			format="json",
		)
		self.assertEqual(retry.status_code, 200)
		self.assertEqual(retry.data["status"], "pending")

# Create your tests here.
