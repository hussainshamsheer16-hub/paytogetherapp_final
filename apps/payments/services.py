from django.db import transaction
from django.utils import timezone

from apps.reports.models import SettlementPayment

from .providers import ProviderUnavailable, get_raast_provider


ALLOWED_PROVIDER_TRANSITIONS = {
    "pending": {"processing", "paid", "failed", "cancelled", "expired"},
    "processing": {"paid", "failed", "cancelled", "expired"},
}


def transition_provider_payment(payment, new_status, reference=""):
    """Apply a verified provider result once; never move terminal states back."""
    if new_status not in {"pending", "processing", "paid", "failed", "cancelled", "expired"}:
        raise ValueError("Unsupported provider payment status.")
    with transaction.atomic():
        payment = SettlementPayment.objects.select_for_update().get(pk=payment.pk)
        if payment.status in {"paid", "failed", "cancelled", "expired"}:
            return payment
        if new_status != payment.status and new_status not in ALLOWED_PROVIDER_TRANSITIONS.get(payment.status, set()):
            raise ValueError("Invalid payment status transition.")
        payment.status = new_status
        if reference:
            payment.provider_reference = reference
            payment.transaction_reference = reference
        if new_status == "paid":
            payment.paid_at = timezone.now()
            payment.approved_at = payment.paid_at
        payment.save(update_fields=["status", "provider_reference", "transaction_reference", "paid_at", "approved_at", "updated_at"])
        return payment


def initiate_raast_payment(payment, provider=None):
    result = (provider or get_raast_provider()).initiate(payment)
    if not result or not result.reference:
        raise ProviderUnavailable("The payment provider returned no reference.")
    payment.provider_reference = result.reference
    payment.transaction_reference = result.reference
    payment.status = "processing"
    payment.save(update_fields=["provider_reference", "transaction_reference", "status", "updated_at"])
    return result


def refresh_raast_payment(payment):
    result = get_raast_provider().verify(payment)
    return transition_provider_payment(payment, result, payment.provider_reference)
