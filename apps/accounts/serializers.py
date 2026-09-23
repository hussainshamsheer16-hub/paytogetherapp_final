from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage



class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    full_name = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "full_name",
            "phone_number",
            "password",
            "confirm_password",
            
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "confirm_password": {"write_only": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        full_name = validated_data.pop("full_name", "")
        first_name = ""
        last_name = ""

        if full_name:
            parts = full_name.strip().split(maxsplit=1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            username=validated_data.get("username", ""),
            phone_number=validated_data.get("phone_number"),
            first_name=first_name,
            last_name=last_name,
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "phone_number",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        return value


class UserUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "phone_number",
        ]

class loginSerializer(serializers.Serializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):

        email= attrs.get("email")
        password= attrs.get("password")

        user = authenticate(email=email, password=password)


        if not user:

            raise serializers.ValidationError({"detail": "Invalid email or password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is inactive."})
        
        attrs["user"] = user

        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()

    def get_full_name(self, user):
        return user.get_full_name().strip()

    def get_profile_image_url(self, user):
        if not user.profile_image:
            return None

        request = self.context.get("request")
        url = default_storage.url(user.profile_image.name)

        if request is not None:
            return request.build_absolute_uri(url)

        return url

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "full_name",
            "phone_number",
            "profile_image",
            "profile_image_url",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "profile_image_url",
        ]
