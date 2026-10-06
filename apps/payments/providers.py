"""Provider boundary for merchant-backed Raast integrations.

No Raast wire protocol is assumed here. A bank/PSP adapter must implement this
contract using its approved integration guide and credentials.
"""
from dataclasses import dataclass
from django.conf import settings
from django.utils.module_loading import import_string


class ProviderUnavailable(Exception):
    pass


@dataclass
class PaymentInitiation:
    reference: str
    redirect_url: str = ""
    instructions: str = ""


class RaastProvider:
    """Contract implemented by an SBP-authorized bank/PSP adapter."""

    def initiate(self, payment):
        raise NotImplementedError

    def verify(self, payment):
        """Return one of pending, processing, paid, failed, cancelled, expired."""
        raise NotImplementedError


class UnconfiguredRaastProvider(RaastProvider):
    def initiate(self, payment):
        raise ProviderUnavailable("Raast payment provider is not configured.")

    def verify(self, payment):
        raise ProviderUnavailable("Raast payment provider is not configured.")


def get_raast_provider():
    provider_class = import_string(
        getattr(settings, "RAAST_PROVIDER_CLASS", "apps.payments.providers.UnconfiguredRaastProvider")
    )
    return provider_class()
