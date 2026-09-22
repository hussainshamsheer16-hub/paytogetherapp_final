from django.urls import path

from .views import (
    LoginPageView,
    LogoutPageView,
    HomePageView,
    RegisterAPIView,
    DashboardPageView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    ProfileUpdateAPIView,
    ChangePasswordAPIView,
    registerpageview,
)

app_name = 'accounts'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('login/', LoginPageView.as_view(), name='login'),
    path('logout/', LogoutPageView.as_view(), name='logout'),
    path('api/register/', RegisterAPIView.as_view(), name='register'),
    path('api/login/', LoginAPIView.as_view(), name='login-api'),
    path('api/logout/', LogoutAPIView.as_view(), name='logout-api'),
    path('api/profile/', ProfileAPIView.as_view(), name='profile'),
    path('api/profile/update/', ProfileUpdateAPIView.as_view(), name='profile-update'),
    path('api/profile/change-password/', ChangePasswordAPIView.as_view(), name='change-password'),
    path('register/', registerpageview.as_view(), name='register-page'),
    path('dashboard/', DashboardPageView.as_view(), name='dashboard'),
]
