from django.urls import path
from .views import (
    CreateTourAPIView,
    CreateTourPageView,
    JoinTourAPIView,
    JoinedTourListAPIView,
    TourDetailAPIView,
    TourListAPIView,
    TourListPageView,
    TourMembersListAPIView,
)

app_name = "tours"

urlpatterns = [
    path(
        "api/tours/create/",
        CreateTourAPIView.as_view(),
        name="create-tour",
    ),
     path(
        "api/tours/<int:pk>/",
        TourDetailAPIView.as_view(),
        name="tour-detail-api"
    ),
    path(
        "tours/create/",
        CreateTourPageView.as_view(),
        name="create-tour-page",
    ),
    path(
        "api/tours/",
        TourListAPIView.as_view(),
        name="tour-list",
    ),
    path(
        "api/tours/joined/",
        JoinedTourListAPIView.as_view(),
        name="joined-tour-list",
    ),
    path(
        "api/tours/join/",
        JoinTourAPIView.as_view(),
        name="join-tour",
    ),
    path(
        "api/tours/<int:tour_id>/members/",
        TourMembersListAPIView.as_view(),
        name="tour-members",
    ),
    path(
        "tours/",
        TourListPageView.as_view(),
        name="tour-list-page",
    ),

]