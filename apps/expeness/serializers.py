from rest_framework import serializers

from apps.tour.models import TourMember

from .models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by_name = serializers.SerializerMethodField()
    added_by_name = serializers.SerializerMethodField()
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "tour",
            "paid_by",
            "paid_by_name",
            "added_by",
            "added_by_name",
            "amount",
            "category",
            "category_display",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "tour", "added_by", "created_at", "updated_at"]

    def get_paid_by_name(self, obj):
        return (obj.paid_by.get_full_name() or obj.paid_by.username or obj.paid_by.email)

    def get_added_by_name(self, obj):
        return (obj.added_by.get_full_name() or obj.added_by.username or obj.added_by.email)

    def validate_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_paid_by(self, paid_by):
        tour = self.context.get("tour")
        if tour is None:
            return paid_by

        is_creator = tour.created_by_id == paid_by.id
        is_member = TourMember.objects.filter(tour=tour, user=paid_by).exists()

        if not (is_creator or is_member):
            raise serializers.ValidationError(
                "The payer must be a member of this tour."
            )
        return paid_by
