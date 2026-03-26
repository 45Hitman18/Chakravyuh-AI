from django.urls import path
from . import views

app_name = "logs"

urlpatterns = [
    path("", views.audit_log_list, name="audit_log_list"),
    path("system/", views.system_log_list, name="system_log_list"),
]
