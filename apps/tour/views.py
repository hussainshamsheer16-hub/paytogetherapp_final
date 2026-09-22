from django.shortcuts import render
from django.views.generic import TemplateView
# Create your views here.

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .Pagination import TourPagination
from rest_framework.filters import SearchFilter,OrderingFilter
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q


from .models import Tour, TourMember
from .serializers import TourSerializer, TourMemberSerializer

from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from apps.core.permissions import IsTourParticipant


def edit_tour_page(request, tour_id):
    return render(request, "tours/edit-tour.html", {"tour_id": tour_id})


def tour_detail_page(request, tour_id):
    return render(request, "tours/tour-detail.html", {"tour_id": tour_id})


def share_tour_page(request, tour_id):
    return render(request, "tours/share-tour.html", {"tour_id": tour_id})


class TourDetailAPIView(
    generics.RetrieveUpdateDestroyAPIView
):

    serializer_class = TourSerializer

    permission_classes = [
        IsAuthenticated
    ]

    parser_classes = [
        MultiPartParser, FormParser
        ]


    def get_queryset(self):
        queryset = Tour.objects.filter(created_by=self.request.user)

        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            joined_tours = TourMember.objects.filter(
                user=self.request.user
            ).values("tour_id")
            queryset = Tour.objects.filter(
                Q(created_by=self.request.user) | Q(id__in=joined_tours)
            ).distinct()

        return queryset


def join_tour_page(request):
    return render(request, "tours/join-tour.html")


class TourListPageView(TemplateView):
    template_name = "tours/tour-list.html"

class TourListAPIView(generics.ListAPIView):
    serializer_class = TourSerializer
    permission_classes = [IsAuthenticated]

    
    parser_classes = [
        MultiPartParser, FormParser
    ]

    pagination_class = TourPagination

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]
    search_fields = [
        "title",
        "destination",
        "status",
    ]
    ordering_fields = [
        "created_at",
        "budget",
        "start_date",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        return Tour.objects.filter(
            created_by=self.request.user
            ).order_by("-created_at")


    
class CreateTourPageView(TemplateView):
    template_name = "tours/create-tour.html"

class CreateTourAPIView(generics.CreateAPIView):
    serializer_class = TourSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

# simple api view
# class CreateTourAPIView(APIView):

#     permission_classes = [IsAuthenticated]

#     def post(self,request):
#         serializer = TourSerializer(
#             data=request.data
#         )

#         if serializer.is_valid():

class JoinedTourListAPIView(generics.ListAPIView):
    serializer_class = TourSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Tour.objects.filter(
            members__user=self.request.user,
        ).order_by("-created_at")

class JoinTourAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        join_code = str(request.data.get("join_code", "")).strip().upper()

        if not join_code:
            return Response(
                {"detail": "join_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tour = Tour.objects.get(join_code=join_code)
        except Tour.DoesNotExist:
            return Response(
                {"detail": "Tour not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if TourMember.objects.filter(tour=tour, user=request.user).exists():
            return Response(
                {"detail": "You have already joined this tour."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member = TourMember.objects.create(tour=tour, user=request.user)
        return Response(
            {
                "success": True,
                "message": "Tour joined successfully.",
                "tour": TourSerializer(tour).data,
                "joined_at": member.joined_at,
            },
            status=status.HTTP_201_CREATED,
        )

class TourMembersListAPIView(APIView):
    """Lists everyone tied to a tour: the creator plus everyone who joined."""

    permission_classes = [IsAuthenticated, IsTourParticipant]

    def get_tour(self):
        if not hasattr(self, "_tour"):
            self._tour = get_object_or_404(Tour, pk=self.kwargs["tour_id"])
        return self._tour

    def get(self, request, tour_id):
        tour = self.get_tour()

        members = list(
            TourMember.objects.filter(tour=tour).select_related("user")
        )
        already_listed = {member.user_id for member in members}

        data = []
        if tour.created_by_id not in already_listed:
            data.append(
                {
                    "id": None,
                    "role": "creator",
                    "joined_at": tour.created_at,
                    "user": {
                        "id": tour.created_by_id,
                        "email": tour.created_by.email,
                        "username": tour.created_by.username,
                        "name": (
                            tour.created_by.get_full_name().strip()
                            or tour.created_by.username
                            or tour.created_by.email
                        ),
                    },
                }
            )
        data.extend(TourMemberSerializer(members, many=True).data)

        return Response(data)


#             tour = serializer.save(
#                 created_by=request.user
#             )

#             return Response(
#                 {
#                     "success": True,
#                     "message": "Tour created successfully.",
#                     "tour": TourSerializer(tour).data,
#                 },

#                 status=status.HTTP_201_CREATED,

#             )
#         return Response(

#             serializer.error,
#             status=status.HTTP_201_BAD_REQUEST,
#         )
