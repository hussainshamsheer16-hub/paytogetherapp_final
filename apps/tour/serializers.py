from rest_framework import serializers

from apps.accounts.models import User

from .models import Tour, TourMember


class TourMemberUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "username", "name"]

    def get_name(self, user):
        return user.get_full_name().strip() or user.username or user.email


class TourMemberSerializer(serializers.ModelSerializer):
    user = TourMemberUserSerializer(read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = TourMember
        fields = ["id", "user", "role", "joined_at"]

    def get_role(self, obj):
        return "creator" if obj.tour.created_by_id == obj.user_id else "member"


class TourSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get("request")
        url = obj.image.url

        if request is not None:
            return request.build_absolute_uri(url)

        return url

    class Meta:
        model = Tour
        fields ="__all__"

        read_only_fields = [
            "id",
            "created_by",
            "join_code",
            "created_at",
            "updated_at",
            "image_url",
        ]


    def validate(self, attrs):

        if attrs.get("end_date") and attrs.get("start_date") and attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {
                    "end_date":
                    "End date cannot be earlier than start date."
                }
            )

        if attrs.get("budget") is not None and attrs["budget"] < 0:

            raise serializers.ValidationError(
                {
                    "budget":
                    "Budget cannot be negative."
                }
            )
        return attrs
