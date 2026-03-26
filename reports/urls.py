from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_list_view, name='report_list'),
    path('create/', views.report_create_view, name='report_create'),
    path('<uuid:report_id>/', views.report_detail_view, name='report_detail'),
    path('<uuid:report_id>/review/', views.report_review_view, name='report_review'),
    path('<uuid:report_id>/escalate/', views.report_escalate_view, name='report_escalate'),
]
