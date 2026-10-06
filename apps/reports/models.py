from django.db import models

from apps.tour.models import Tour


class SettlementPayment(models.Model):
	PAYMENT_METHOD_CHOICES = [
		("cod", "Cash on delivery"),
		("card", "Bank card"),
		("raast", "Raast"),
	]
	STATUS_CHOICES = [
		("unpaid", "Unpaid"),
		("pending", "Pending approval"),
		("paid", "Paid"),
		("received", "Received"),
		("not_received", "Not received"),
		("failed", "Failed"),
		("cancelled", "Cancelled"),
		("processing", "Processing"),
		("expired", "Expired"),
	]

	tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="settlement_payments")
	payer = models.ForeignKey(
		"accounts.User", on_delete=models.CASCADE, related_name="settlement_payments_sent"
	)
	recipient = models.ForeignKey(
		"accounts.User", on_delete=models.CASCADE, related_name="settlement_payments_received"
	)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
	status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="unpaid")
	paid_at = models.DateTimeField(null=True, blank=True)
	approved_at = models.DateTimeField(null=True, blank=True)
	stripe_checkout_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
	stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
	transaction_reference = models.CharField(max_length=255, blank=True)
	provider_reference = models.CharField(max_length=255, blank=True, db_index=True)
	sender_raast_id = models.CharField(max_length=255, blank=True)
	recipient_raast_id = models.CharField(max_length=255, blank=True)
	currency = models.CharField(max_length=3, default="usd")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]
		constraints = [
			models.UniqueConstraint(
				fields=["tour", "payer", "recipient", "amount"],
				name="unique_tour_settlement_payment",
			)
		]

	def __str__(self):
		return f"{self.payer} pays {self.recipient} - {self.amount} ({self.status})"


class Notification(models.Model):
	user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
	payment = models.ForeignKey(SettlementPayment, on_delete=models.CASCADE, related_name="notifications")
	title = models.CharField(max_length=200)
	message = models.TextField()
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.user}: {self.title}"

# Create your models here.
