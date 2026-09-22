from rest_framework.permissions import BasePermission

from apps.tour.models import Tour, TourMember


def user_is_tour_participant(user, tour):
    """A tour's creator or any joined member counts as a participant."""
    if tour.created_by_id == user.id:
        return True
    return TourMember.objects.filter(tour=tour, user=user).exists()


class IsTourParticipant(BasePermission):
    """
    Grants access only to the tour's creator or one of its joined members.
    Expects the view to expose the target tour via `get_tour()`.
    """

    message = "You must be a member of this tour to access it."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        tour = view.get_tour()
        if tour is None:
            return False

        return user_is_tour_participant(request.user, tour)
