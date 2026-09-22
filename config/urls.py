"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import sys

from django.contrib import admin
from django.contrib.staticfiles.views import serve as serve_static
from django.http import HttpResponse
from django.views.static import serve as serve_media
from django.urls import include, path, re_path

from django.conf import settings

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path("health/", lambda request: HttpResponse("ok", content_type="text/plain"), name="health"),
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls', namespace='accounts')),
    path('',include('apps.tour.urls', namespace='tours')),
    path('', include('apps.expeness.urls', namespace='expenses')),
    path('', include('apps.reports.urls', namespace='reports')),
    path('', include('apps.payments.urls', namespace='payments')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('apps.tour.page_urls', namespace='tours-page')),
]

# Let Django's development server serve assets even when a local environment
# uses DEBUG=release. Production deployments should serve static files via the
# web server or CDN instead.
if settings.DEBUG or "runserver" in sys.argv:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", serve_static, {"insecure": True}),
    ]

if settings.SERVE_MEDIA or "runserver" in sys.argv:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve_media,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
