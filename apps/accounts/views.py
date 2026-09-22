from django.contrib.auth import logout as django_logout
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.permissions import (AllowAny,IsAuthenticated)   
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .forms import RegisterForm
from .serializers import (
    RegisterSerializer,
    loginSerializer,
    ProfileSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)


from django.shortcuts import render


def dashboard(request):
    return render(request, 'dashboard.html')


class LoginPageView(auth_views.LoginView):
    template_name = "auth/login.html"


class LogoutPageView(auth_views.LogoutView):
    next_page = "accounts:login"  # Redirect to login page after logout

class DashboardPageView(TemplateView):
    template_name = "Dashboard/dashboard.html"


class HomePageView(TemplateView):
    """Render the public landing page at the site root."""

    template_name = "home.html"


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)


class ProfileUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Profile updated successfully.",
                    "data": ProfileSerializer(request.user).data,
                }
            )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return Response(
                {"success": False, "message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"success": True, "message": "Password updated successfully."}
        )


class LogoutAPIView(APIView):
    # Logging out is safe even when the JWT has already expired. This lets the
    # browser clear stale local tokens without receiving a second 401 response.
    permission_classes = [AllowAny]

    def post(self, request):
        django_logout(request)
        return Response({"success": True, "message": "Logged out successfully."})

    
class registerpageview(TemplateView):
    template_name = "auth/register.html"

    def get(self, request, *args, **kwargs):
        form = RegisterForm()
        return render(request, self.template_name, {"form": form})

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "User registered successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "success": False,
                "message": "Failed to register user.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = loginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "message": "User logged in successfully.",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "phone_number": user.phone_number,
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
        )
