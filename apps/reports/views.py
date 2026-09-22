from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsTourParticipant
from apps.expeness.models import Expense
from apps.tour.models import Tour, TourMember

from .models import Notification, SettlementPayment

TWO_PLACES = Decimal("0.01")


def _quantize(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _display_name(user):
    return user.get_full_name().strip() or user.username or user.email


def build_tour_report(tour):
    expenses = Expense.objects.filter(tour=tour).select_related("paid_by")

    total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    participants = {tour.created_by_id: tour.created_by}
    for member in TourMember.objects.filter(tour=tour).select_related("user"):
        participants[member.user_id] = member.user

    member_count = len(participants) or 1
    share_per_member = _quantize(total / member_count)

    paid_totals = {
        row["paid_by"]: row["amount_sum"]
        for row in expenses.values("paid_by").annotate(amount_sum=Sum("amount"))
    }

    members_report = []
    for user_id, user in participants.items():
        paid = _quantize(paid_totals.get(user_id, Decimal("0")))
        balance = _quantize(paid - share_per_member)
        members_report.append(
            {
                "user_id": user_id,
                "name": _display_name(user),
                "email": user.email,
                "paid": str(paid),
                "share": str(share_per_member),
                "balance": str(balance),
                "status": "gets back" if balance > 0 else (
                    "owes" if balance < 0 else "settled"
                ),
            }
        )
    members_report.sort(key=lambda item: item["name"].lower())

    category_totals = {
        row["category"]: str(_quantize(row["amount_sum"]))
        for row in expenses.values("category").annotate(amount_sum=Sum("amount"))
    }

    settlements = _settle_up(members_report)

    return {
        "tour_id": tour.id,
        "tour_title": tour.title,
        "total_expense": str(_quantize(total)),
        "member_count": member_count,
        "share_per_member": str(share_per_member),
        "members": members_report,
        "category_totals": category_totals,
        "settlements": settlements,
    }


def _settle_up(members_report):
    """
    Simple greedy settle-up: match the biggest creditor against the biggest
    debtor, repeatedly, until every balance is (near) zero. Keeps the number
    of transactions needed to settle the group to a minimum in practice.
    """
    creditors = []
    debtors = []
    for member in members_report:
        balance = Decimal(member["balance"])
        if balance > 0:
            creditors.append([member["user_id"], member["name"], balance])
        elif balance < 0:
            debtors.append([member["user_id"], member["name"], -balance])

    creditors.sort(key=lambda item: item[2], reverse=True)
    debtors.sort(key=lambda item: item[2], reverse=True)

    settlements = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debtor_name, debtor_amount = debtors[i]
        creditor_id, creditor_name, creditor_amount = creditors[j]
        settle_amount = min(debtor_amount, creditor_amount)

        if settle_amount > 0:
            settlements.append(
                {
                    "from_id": debtor_id,
                    "from": debtor_name,
                    "to_id": creditor_id,
                    "to": creditor_name,
                    "amount": str(_quantize(settle_amount)),
                }
            )

        debtors[i][2] -= settle_amount
        creditors[j][2] -= settle_amount

        if debtors[i][2] <= Decimal("0.01"):
            i += 1
        if creditors[j][2] <= Decimal("0.01"):
            j += 1

    return settlements


class TourReportAPIView(APIView):
    permission_classes = [IsAuthenticated, IsTourParticipant]

    def get_tour(self):
        if not hasattr(self, "_tour"):
            self._tour = get_object_or_404(Tour, pk=self.kwargs["tour_id"])
        return self._tour

    def get(self, request, tour_id):
        tour = self.get_tour()
        report = build_tour_report(tour)
        payments = SettlementPayment.objects.filter(tour=tour)
        payment_lookup = {
            (payment.payer_id, payment.recipient_id, str(_quantize(payment.amount))): payment
            for payment in payments
        }
        for settlement in report["settlements"]:
            payment = payment_lookup.get(
                (settlement["from_id"], settlement["to_id"], settlement["amount"])
            )
            settlement["status"] = payment.status if payment else "unpaid"
            settlement["payment_method"] = payment.payment_method if payment else None
            settlement["payment_id"] = payment.id if payment else None
        return Response(report)


class SettlementPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsTourParticipant]

    def get_tour(self):
        if not hasattr(self, "_tour"):
            self._tour = get_object_or_404(Tour, pk=self.kwargs["tour_id"])
        return self._tour

    def post(self, request, tour_id):
        tour = self.get_tour()
        payer_id = request.user.id
        try:
            recipient_id = int(request.data["to_id"])
            amount = _quantize(request.data["amount"])
        except (KeyError, TypeError, ValueError, ArithmeticError):
            return Response({"detail": "A valid recipient and amount are required."}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = request.data.get("payment_method")
        if payment_method not in dict(SettlementPayment.PAYMENT_METHOD_CHOICES):
            return Response({"detail": "Payment method must be cod or card."}, status=status.HTTP_400_BAD_REQUEST)
        if payment_method == "card":
            return Response(
                {"detail": "Bank card payments must use Stripe Checkout."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        settlement = next(
            (
                item for item in build_tour_report(tour)["settlements"]
                if item["from_id"] == payer_id
                and item["to_id"] == recipient_id
                and item["amount"] == str(amount)
            ),
            None,
        )
        if settlement is None:
            return Response({"detail": "This payment is not a current settlement."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            payment, _ = SettlementPayment.objects.update_or_create(
                tour=tour,
                payer_id=payer_id,
                recipient_id=recipient_id,
                amount=amount,
                defaults={
                    "payment_method": payment_method,
                    "status": "pending",
                    "paid_at": None,
                    "approved_at": None,
                },
            )

            sender_name = _display_name(request.user)
            Notification.objects.create(
                user=payment.recipient,
                payment=payment,
                title="Money received",
                message=(
                    f"You received a payment of Rs {payment.amount} from {sender_name}. "
                    "Please confirm whether you received it."
                ),
            )

        return Response(
            {
                "id": payment.id,
                "status": payment.status,
                "payment_method": payment.payment_method,
                "paid_at": payment.paid_at,
            },
            status=status.HTTP_200_OK,
        )


class SettlementPaymentApprovalAPIView(APIView):
    permission_classes = [IsAuthenticated, IsTourParticipant]

    def get_tour(self):
        if not hasattr(self, "_tour"):
            self._tour = get_object_or_404(Tour, pk=self.kwargs["tour_id"])
        return self._tour

    def post(self, request, tour_id, payment_id):
        payment = get_object_or_404(
            SettlementPayment,
            id=payment_id,
            tour=self.get_tour(),
            status="pending",
        )
        if payment.recipient_id != request.user.id:
            return Response(
                {"detail": "Only the recipient can approve this payment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        decision = (request.data.get("decision") or "received").strip().lower()
        if decision not in {"received", "not_received", "not_confirmed"}:
            return Response(
                {"detail": "Decision must be received or not_confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_decision = "not_received" if decision in {"not_received", "not_confirmed"} else "received"

        now = timezone.now()
        if normalized_decision == "received":
            payment.status = "paid"
            payment.paid_at = now
            payment.approved_at = now
            title = "Payment received"
            message = f"{_display_name(request.user)} marked the payment of Rs {payment.amount} as received."
        else:
            payment.status = "not_received"
            payment.paid_at = None
            payment.approved_at = now
            title = "Payment not confirmed"
            message = (
                f"{_display_name(request.user)} could not confirm the payment of Rs {payment.amount}. "
                "Please check this transaction again."
            )

        payment.save(update_fields=["status", "paid_at", "approved_at", "updated_at"])
        Notification.objects.create(
            user=payment.payer,
            payment=payment,
            title=title,
            message=message,
        )
        return Response(
            {"status": payment.status, "approved_at": payment.approved_at},
            status=status.HTTP_200_OK,
        )


class NotificationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
        payload = []
        for item in notifications:
            payload.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "message": item.message,
                    "is_read": item.is_read,
                    "created_at": item.created_at.isoformat(),
                    "payment_id": item.payment_id,
                    "tour_id": item.payment.tour_id,
                    "can_approve": (
                        not item.is_read
                        and item.payment.status == "pending"
                        and item.payment.recipient_id == request.user.id
                    ),
                }
            )
        return Response(
            {"count": notifications.filter(is_read=False).count(), "notifications": payload},
            status=status.HTTP_200_OK,
        )


class NotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"] if hasattr(notification, "updated_at") else ["is_read"])
        return Response({"success": True}, status=status.HTTP_200_OK)


class DashboardSummaryAPIView(APIView):
    """Aggregates a quick snapshot across every tour the user takes part in."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        joined_tour_ids = TourMember.objects.filter(user=user).values_list(
            "tour_id", flat=True
        )
        tours = Tour.objects.filter(
            models_q_created_or_joined(user, joined_tour_ids)
        ).distinct()

        member_ids = {user.id}
        total_expenses = Decimal("0")
        balance = Decimal("0")

        for tour in tours:
            report = build_tour_report(tour)
            for member in report["members"]:
                member_ids.add(member["user_id"])
                if member["user_id"] == user.id:
                    balance += Decimal(member["balance"])
            total_expenses += Decimal(report["total_expense"])

        return Response(
            {
                "total_tours": tours.count(),
                "total_members": len(member_ids),
                "total_expenses": str(_quantize(total_expenses)),
                "balance": str(_quantize(balance)),
            }
        )


def models_q_created_or_joined(user, joined_tour_ids):
    from django.db.models import Q

    return Q(created_by=user) | Q(id__in=list(joined_tour_ids))
