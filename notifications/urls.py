from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("mark-read/<uuid:notification_id>/", views.mark_notification_read, name="mark_notification_read"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
]
