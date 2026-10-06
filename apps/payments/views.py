from decimal import Decimal, InvalidOperation
import base64

import qrcode
from qrcode.image.svg import SvgPathFillImage
import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports.models import Notification, SettlementPayment
from apps.reports.views import _quantize, build_tour_report
from apps.tour.models import Tour
from .providers import ProviderUnavailable, UnconfiguredRaastProvider, get_raast_provider
from .services import initiate_raast_payment, refresh_raast_payment

stripe.api_key = settings.STRIPE_SECRET_KEY

ZERO_DECIMAL_CURRENCIES = {
    "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg",
    "rwf", "ugx", "vnd", "vuv", "xaf", "xof", "xpf",
}


def _minor_amount(amount, currency):
    amount = Decimal(amount)
    return int(amount if currency in ZERO_DECIMAL_CURRENCIES else amount * 100)


def _current_settlement(tour, payer_id, recipient_id):
    for settlement in build_tour_report(tour)["settlements"]:
        if (
            settlement["from_id"] == payer_id
            and settlement["to_id"] == recipient_id
        ):
            return settlement
    return None


def _payment_from_event(event_object):
    metadata = event_object.get("metadata") or {}
    payment_id = metadata.get("payment_id")
    if payment_id:
        try:
            return SettlementPayment.objects.filter(pk=int(payment_id)).first()
        except (TypeError, ValueError):
            return None
    session_id = event_object.get("id")
    if session_id:
        return SettlementPayment.objects.filter(
            stripe_checkout_session_id=session_id
        ).first()
    payment_intent_id = event_object.get("payment_intent") or event_object.get("id")
    if payment_intent_id:
        return SettlementPayment.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()
    return None


class StripeCheckoutSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"success": False, "message": "Stripe payments are not configured on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            tour_id = int(request.data["tour_id"])
            recipient_id = int(request.data["to_id"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {"success": False, "message": "A valid tour and recipient are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tour = Tour.objects.filter(pk=tour_id).first()
        if not tour or not (
            tour.created_by_id == request.user.id
            or tour.members.filter(user_id=request.user.id).exists()
        ):
            return Response(
                {"success": False, "message": "You cannot pay this tour settlement."},
                status=status.HTTP_404_NOT_FOUND,
            )

        settlement = _current_settlement(tour, request.user.id, recipient_id)
        if not settlement:
            return Response(
                {"success": False, "message": "This payment is not a current settlement."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = _quantize(settlement["amount"])
        if amount <= 0:
            return Response(
                {"success": False, "message": "The payment amount is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        currency = settings.STRIPE_CURRENCY
        if len(currency) != 3 or not currency.isalpha():
            return Response(
                {"success": False, "message": "Stripe currency is not configured correctly."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            payment = (
                SettlementPayment.objects.select_for_update()
                .filter(
                    tour=tour,
                    payer_id=request.user.id,
                    recipient_id=recipient_id,
                    amount=amount,
                )
                .first()
            )
            if payment and payment.status == "paid":
                return Response(
                    {"success": False, "message": "This payment is already paid."},
                    status=status.HTTP_409_CONFLICT,
                )
            if payment and payment.status == "pending" and payment.stripe_checkout_session_id:
                try:
                    session = stripe.checkout.Session.retrieve(
                        payment.stripe_checkout_session_id
                    )
                    return Response({"success": True, "checkout_url": session.url})
                except stripe.error.StripeError:
                    payment.stripe_checkout_session_id = None

            if payment and payment.status == "pending" and payment.payment_method == "cod":
                return Response(
                    {"success": False, "message": "A payment is already awaiting approval."},
                    status=status.HTTP_409_CONFLICT,
                )

            if not payment:
                payment = SettlementPayment.objects.create(
                    tour=tour,
                    payer_id=request.user.id,
                    recipient_id=recipient_id,
                    amount=amount,
                    payment_method="card",
                    status="pending",
                    currency=currency,
                )
            else:
                payment.payment_method = "card"
                payment.status = "pending"
                payment.currency = currency

            success_url = request.build_absolute_uri(
                "/payments/success/?session_id={CHECKOUT_SESSION_ID}"
            )
            cancel_url = request.build_absolute_uri(
                f"/payments/cancel/?payment_id={payment.id}"
            )
            try:
                session = stripe.checkout.Session.create(
                    mode="payment",
                    payment_method_types=["card"],
                    line_items=[
                        {
                            "price_data": {
                                "currency": currency,
                                "product_data": {
                                    "name": f"Tour settlement: {tour.title}",
                                },
                                "unit_amount": _minor_amount(amount, currency),
                            },
                            "quantity": 1,
                        }
                    ],
                    metadata={
                        "payment_id": str(payment.id),
                        "tour_id": str(tour.id),
                        "user_id": str(request.user.id),
                    },
                    payment_intent_data={
                        "metadata": {"payment_id": str(payment.id)},
                    },
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
            except stripe.error.StripeError:
                return Response(
                    {"success": False, "message": "Unable to create Stripe checkout session."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            payment.stripe_checkout_session_id = session.id
            payment.transaction_reference = session.id
            payment.save(
                update_fields=[
                    "payment_method",
                    "status",
                    "currency",
                    "stripe_checkout_session_id",
                    "transaction_reference",
                    "updated_at",
                ]
            )

        return Response({"success": True, "checkout_url": session.url})


class PaymentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        payment_id = request.query_params.get("payment_id")
        payment = None
        if session_id:
            payment = SettlementPayment.objects.filter(
                stripe_checkout_session_id=session_id
            ).first()
        elif payment_id:
            payment = SettlementPayment.objects.filter(pk=payment_id).first()

        if not payment or request.user.id not in {payment.payer_id, payment.recipient_id}:
            return Response(
                {"success": False, "message": "Payment was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if payment.payment_method == "raast" and payment.status in {"pending", "processing"}:
            try:
                payment = refresh_raast_payment(payment)
            except ProviderUnavailable:
                pass
            except (TimeoutError, ConnectionError):
                pass
            except ValueError:
                pass
        return Response(
            {
                "success": True,
                "status": payment.status,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "transaction_reference": payment.transaction_reference,
                "provider_reference": payment.provider_reference if payment.payment_method == "raast" else "",
            }
        )


class RaastPaymentAPIView(APIView):
    """Start or resume Raast via an explicitly configured bank/PSP adapter."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            tour_id = int(request.data["tour_id"])
            recipient_id = int(request.data["to_id"])
        except (KeyError, TypeError, ValueError):
            return Response({"message": "A valid tour and recipient are required."}, status=400)
        tour = Tour.objects.filter(pk=tour_id).first()
        if not tour or not (tour.created_by_id == request.user.id or tour.members.filter(user_id=request.user.id).exists()):
            return Response({"message": "You cannot pay this settlement."}, status=404)
        settlement = _current_settlement(tour, request.user.id, recipient_id)
        if not settlement:
            return Response({"message": "This is not a current settlement."}, status=400)
        amount = _quantize(settlement["amount"])
        if amount <= 0:
            return Response({"message": "The payment amount is invalid."}, status=400)
        provider = get_raast_provider()
        if isinstance(provider, UnconfiguredRaastProvider):
            return Response({"message": "Raast is not configured. Connect a participating bank or PSP adapter."}, status=503)
        with transaction.atomic():
            payment = SettlementPayment.objects.select_for_update().filter(
                tour=tour, payer=request.user, recipient_id=recipient_id, amount=amount
            ).first()
            if payment and payment.status in {"paid", "pending"} and payment.payment_method != "raast":
                return Response({"message": "Another payment is already awaiting confirmation."}, status=409)
            if payment and payment.status == "paid":
                return Response({"message": "This settlement is already paid."}, status=409)
            if not payment:
                payment = SettlementPayment.objects.create(
                    tour=tour, payer=request.user, recipient_id=recipient_id,
                    amount=amount, payment_method="raast", status="pending", currency="pkr",
                )
            elif payment.status in {"failed", "cancelled", "expired", "not_received"}:
                payment.payment_method = "raast"
                payment.status = "pending"
                payment.paid_at = None
                payment.provider_reference = ""
                payment.save(update_fields=["payment_method", "status", "paid_at", "provider_reference", "updated_at"])
            elif payment.payment_method != "raast":
                payment.payment_method = "raast"
                payment.status = "pending"
                payment.save(update_fields=["payment_method", "status", "updated_at"])
            elif payment.status == "processing" and payment.provider_reference:
                return Response({"success": True, "status": payment.status, "payment_id": payment.id}, status=200)
            try:
                result = initiate_raast_payment(payment, provider=provider)
            except ProviderUnavailable:
                return Response({"message": "Raast is not configured. Connect a participating bank or PSP adapter."}, status=503)
            except (TimeoutError, ConnectionError):
                return Response({"message": "The payment provider did not respond. Check payment status before retrying."}, status=502)
        payload = {"success": True, "status": payment.status, "payment_id": payment.id}
        if result.redirect_url:
            payload["redirect_url"] = result.redirect_url
        if result.instructions:
            payload["instructions"] = result.instructions
        return Response(payload, status=200)


class RaastManualPaymentAPIView(APIView):
    """Record a payer-reported transfer for recipient review; this is not bank verification."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            tour_id = int(request.data["tour_id"])
            recipient_id = int(request.data["to_id"])
        except (KeyError, TypeError, ValueError):
            return Response({"message": "A valid tour and recipient are required."}, status=400)

        sender_raast_id = str(request.data.get("sender_raast_id", "")).strip()
        recipient_raast_id = str(request.data.get("recipient_raast_id", "")).strip()
        if not sender_raast_id or not recipient_raast_id:
            return Response({"message": "Enter both sender and receiver Raast IDs."}, status=400)
        if len(sender_raast_id) > 255 or len(recipient_raast_id) > 255:
            return Response({"message": "Raast IDs must be 255 characters or fewer."}, status=400)

        tour = Tour.objects.filter(pk=tour_id).first()
        if not tour or not (tour.created_by_id == request.user.id or tour.members.filter(user_id=request.user.id).exists()):
            return Response({"message": "You cannot pay this settlement."}, status=404)
        settlement = _current_settlement(tour, request.user.id, recipient_id)
        if not settlement:
            return Response({"message": "This is not a current settlement."}, status=400)

        amount = _quantize(settlement["amount"])
        sender_name = request.user.get_full_name().strip() or request.user.username or request.user.email
        with transaction.atomic():
            payment = SettlementPayment.objects.select_for_update().filter(
                tour=tour, payer=request.user, recipient_id=recipient_id, amount=amount
            ).first()
            if payment and payment.status == "paid":
                return Response({"message": "This settlement is already paid."}, status=409)
            if payment and payment.status == "pending":
                if payment.payment_method == "raast" and payment.sender_raast_id == sender_raast_id and payment.recipient_raast_id == recipient_raast_id:
                    return Response({"success": True, "payment_id": payment.id, "status": "pending"}, status=200)
                return Response({"message": "A payment request is already awaiting recipient approval."}, status=409)
            if not payment:
                payment = SettlementPayment.objects.create(
                    tour=tour,
                    payer=request.user,
                    recipient_id=recipient_id,
                    amount=amount,
                    payment_method="raast",
                    status="pending",
                    currency="pkr",
                    sender_raast_id=sender_raast_id,
                    recipient_raast_id=recipient_raast_id,
                )
            else:
                payment.payment_method = "raast"
                payment.status = "pending"
                payment.currency = "pkr"
                payment.paid_at = None
                payment.approved_at = None
                payment.sender_raast_id = sender_raast_id
                payment.recipient_raast_id = recipient_raast_id
                payment.save(update_fields=[
                    "payment_method", "status", "currency", "paid_at", "approved_at",
                    "sender_raast_id", "recipient_raast_id", "updated_at",
                ])

            Notification.objects.create(
                user=payment.recipient,
                payment=payment,
                title="Raast transfer awaiting confirmation",
                message=(
                    f"{sender_name} reports sending Rs {payment.amount} via Raast. "
                    f"Sender Raast ID: {sender_raast_id}. Receiver Raast ID: {recipient_raast_id}. "
                    "Check your bank account before confirming receipt."
                ),
            )
        return Response({"success": True, "payment_id": payment.id, "status": "pending"}, status=200)


class RaastPaymentLinkAPIView(APIView):
    """Return a QR for a PayTogether page that can resume this valid settlement."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            tour_id = int(request.data["tour_id"])
            recipient_id = int(request.data["to_id"])
        except (KeyError, TypeError, ValueError):
            return Response({"message": "A valid tour and recipient are required."}, status=400)

        tour = Tour.objects.filter(pk=tour_id).first()
        if not tour or not (tour.created_by_id == request.user.id or tour.members.filter(user_id=request.user.id).exists()):
            return Response({"message": "You cannot pay this settlement."}, status=404)
        settlement = _current_settlement(tour, request.user.id, recipient_id)
        if not settlement:
            return Response({"message": "This is not a current settlement."}, status=400)

        payment_url = request.build_absolute_uri(
            f"/tours/{tour.id}/?pay_to={recipient_id}&method=raast"
        )
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
        qr.add_data(payment_url)
        qr.make(fit=True)
        svg = qr.make_image(image_factory=SvgPathFillImage).to_string(encoding="unicode")
        qr_data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return Response({"payment_url": payment_url, "qr_code": qr_data_uri}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return HttpResponse("Stripe webhook is not configured", status=503)
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(
                request.body,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            return HttpResponse("Invalid payload", status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse("Invalid signature", status=400)

        event_type = event["type"]
        event_object = event["data"]["object"]
        if event_type == "checkout.session.completed":
            self._complete_checkout(event_object)
        elif event_type in {
            "checkout.session.async_payment_failed",
            "checkout.session.expired",
            "payment_intent.payment_failed",
        }:
            self._fail_payment(event_object)
        return HttpResponse("ok", status=200)

    def _complete_checkout(self, session):
        if session.get("payment_status") != "paid":
            return
        payment = _payment_from_event(session)
        if not payment:
            return
        metadata = session.get("metadata") or {}
        if (
            metadata.get("payment_id") != str(payment.id)
            or metadata.get("tour_id") != str(payment.tour_id)
            or metadata.get("user_id") != str(payment.payer_id)
            or (
                payment.stripe_checkout_session_id
                and payment.stripe_checkout_session_id != session.get("id")
            )
        ):
            return
        amount_total = session.get("amount_total")
        expected_amount = _minor_amount(payment.amount, payment.currency)
        if amount_total != expected_amount:
            return
        if session.get("currency") and session["currency"].lower() != payment.currency.lower():
            return
        payment_intent_id = session.get("payment_intent") or ""
        with transaction.atomic():
            payment = SettlementPayment.objects.select_for_update().get(pk=payment.pk)
            if payment.status == "paid":
                return
            payment.status = "paid"
            payment.paid_at = timezone.now()
            payment.approved_at = payment.paid_at
            payment.stripe_payment_intent_id = payment_intent_id
            payment.transaction_reference = payment_intent_id or session.get("id", "")
            payment.save(
                update_fields=[
                    "status",
                    "paid_at",
                    "approved_at",
                    "stripe_payment_intent_id",
                    "transaction_reference",
                    "updated_at",
                ]
            )

    def _fail_payment(self, event_object):
        payment = _payment_from_event(event_object)
        if not payment:
            return
        with transaction.atomic():
            payment = SettlementPayment.objects.select_for_update().get(pk=payment.pk)
            if payment.status != "paid":
                payment.status = "cancelled" if event_object.get("object") == "checkout.session" and event_object.get("status") == "expired" else "failed"
                payment.save(update_fields=["status", "updated_at"])


class PaymentSuccessPageView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return render(request, "payments/success.html")


class PaymentCancelPageView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return render(request, "payments/cancel.html")
