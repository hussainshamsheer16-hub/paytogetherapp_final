from django.urls import path

from .views import (
    PaymentCancelPageView,
    PaymentStatusAPIView,
    RaastManualPaymentAPIView,
    RaastPaymentLinkAPIView,
    RaastPaymentAPIView,
    PaymentSuccessPageView,
    StripeCheckoutSessionAPIView,
    StripeWebhookAPIView,
)

app_name = "payments"

urlpatterns = [
    path(
        "api/payments/create-checkout-session/",
        StripeCheckoutSessionAPIView.as_view(),
        name="create-checkout-session",
    ),
    path(
        "api/payments/status/",
        PaymentStatusAPIView.as_view(),
        name="payment-status",
    ),
    path("api/payments/raast/initiate/", RaastPaymentAPIView.as_view(), name="raast-initiate"),
    path("api/payments/raast/manual/", RaastManualPaymentAPIView.as_view(), name="raast-manual"),
    path("api/payments/raast/payment-link/", RaastPaymentLinkAPIView.as_view(), name="raast-payment-link"),
    path(
        "api/payments/stripe/webhook/",
        StripeWebhookAPIView.as_view(),
        name="stripe-webhook",
    ),
    path("payments/success/", PaymentSuccessPageView.as_view(), name="success"),
    path("payments/cancel/", PaymentCancelPageView.as_view(), name="cancel"),
]
