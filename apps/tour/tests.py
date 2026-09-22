from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Tour, TourMember


class JoinTourAPITests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.owner = user_model.objects.create_user(
			email="tour-owner@example.com",
			username="tour-owner",
			password="password123",
		)
		self.member = user_model.objects.create_user(
			email="tour-member@example.com",
			username="tour-member",
			password="password123",
		)
		self.tour = Tour.objects.create(
			created_by=self.owner,
			title="Test Tour",
			destination="Test Destination",
			start_date=date(2026, 10, 1),
			end_date=date(2026, 10, 3),
		)
		self.url = "/api/tours/join/"

	def test_join_validation_and_success(self):
		self.assertEqual(
			self.client.post(
				self.url,
				{"join_code": self.tour.join_code},
				format="json",
			).status_code,
			401,
		)

		self.client.force_authenticate(user=self.member)
		for payload, expected_status in [
			({"join_code": ""}, 400),
			({"join_code": "INVALID"}, 404),
			({"join_code": "NOT-A-REAL-CODE"}, 404),
		]:
			self.assertEqual(
				self.client.post(self.url, payload, format="json").status_code,
				expected_status,
			)

		response = self.client.post(
			self.url,
			{"join_code": self.tour.join_code},
			format="json",
		)
		self.assertEqual(response.status_code, 201)
		self.assertEqual(TourMember.objects.count(), 1)

		self.assertEqual(
			self.client.post(
				self.url,
				{"join_code": self.tour.join_code},
				format="json",
			).status_code,
			400,
		)
