from django.urls import path

from .views import edit_tour_page, join_tour_page, share_tour_page, tour_detail_page

app_name = "tours_page"

urlpatterns = [

    path(
        "tours/<int:tour_id>/",
        tour_detail_page,
        name="tour-detail"
    ),

    path(
        "tours/<int:tour_id>/share/",
        share_tour_page,
        name="share-tour"
    ),

    path(
        "tours/edit/<int:tour_id>/",
        edit_tour_page,
        name="edit-tour"
    ),

    path(
        "tours/join/",
        join_tour_page,
        name="join-tour"
    ),

]
