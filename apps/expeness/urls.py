from django.urls import path

from .views import ExpenseDetailAPIView, ExpenseListCreateAPIView

app_name = "expenses"

urlpatterns = [
    path(
        "api/tours/<int:tour_id>/expenses/",
        ExpenseListCreateAPIView.as_view(),
        name="expense-list-create",
    ),
    path(
        "api/tours/<int:tour_id>/expenses/<int:pk>/",
        ExpenseDetailAPIView.as_view(),
        name="expense-detail",
    ),
]
