from django.urls import path

from .views import (
    DashboardSummaryAPIView,
    NotificationAPIView,
    NotificationReadAPIView,
    SettlementPaymentAPIView,
    SettlementPaymentApprovalAPIView,
    TourReportAPIView,
)

app_name = "reports"

urlpatterns = [
    path(
        "api/tours/<int:tour_id>/report/",
        TourReportAPIView.as_view(),
        name="tour-report",
    ),
    path(
        "api/tours/<int:tour_id>/settlements/pay/",
        SettlementPaymentAPIView.as_view(),
        name="settlement-pay",
    ),
    path(
        "api/tours/<int:tour_id>/settlements/<int:payment_id>/approve/",
        SettlementPaymentApprovalAPIView.as_view(),
        name="settlement-approve",
    ),
    path(
        "api/notifications/",
        NotificationAPIView.as_view(),
        name="notifications",
    ),
    path(
        "api/notifications/<int:notification_id>/read/",
        NotificationReadAPIView.as_view(),
        name="notification-read",
    ),
    path(
        "api/dashboard/summary/",
        DashboardSummaryAPIView.as_view(),
        name="dashboard-summary",
    ),
]
