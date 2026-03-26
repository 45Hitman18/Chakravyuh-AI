"""
URL configuration for chakravyuh project.

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
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from . import views

handler404 = "chakravyuh.views.custom_404"
handler403 = "chakravyuh.views.custom_403"


urlpatterns = [
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("support/", views.support_view, name="support"),
    path("faq/", views.faq_view, name="faq"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("dashboard/", include("dashboard.urls")),
    path("calls/", include("calls.urls")),
    path("analysis/", include("analysis.urls", namespace="analysis")),
    path("reports/", include("reports.urls", namespace="reports")),
    path("honeypot/", include("honeypot.urls")),
    path("logs/", include("logs.urls", namespace="logs")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
