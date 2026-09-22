from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsTourParticipant, user_is_tour_participant
from apps.tour.models import Tour

from .models import Expense
from .serializers import ExpenseSerializer


class TourScopedExpenseMixin:
    """Shared helpers for looking up the tour named in the URL."""

    def get_tour(self):
        if not hasattr(self, "_tour"):
            self._tour = get_object_or_404(Tour, pk=self.kwargs["tour_id"])
        return self._tour

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tour"] = self.get_tour()
        return context


class ExpenseListCreateAPIView(
    TourScopedExpenseMixin, generics.ListCreateAPIView
):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsTourParticipant]

    def get_queryset(self):
        return Expense.objects.filter(tour=self.get_tour()).select_related(
            "paid_by", "added_by"
        )

    def perform_create(self, serializer):
        serializer.save(tour=self.get_tour(), added_by=self.request.user)


class ExpenseDetailAPIView(
    TourScopedExpenseMixin, generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsTourParticipant]

    def get_queryset(self):
        return Expense.objects.filter(tour=self.get_tour()).select_related(
            "paid_by", "added_by"
        )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        is_owner = obj.added_by_id == request.user.id
        is_tour_creator = obj.tour.created_by_id == request.user.id
        if request.method not in ("GET", "HEAD", "OPTIONS") and not (
            is_owner or is_tour_creator
        ):
            self.permission_denied(
                request,
                message="Only the person who added this expense or the tour "
                "creator can edit or delete it.",
            )
