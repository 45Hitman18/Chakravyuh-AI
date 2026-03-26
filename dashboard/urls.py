from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('upload-audio/', views.dashboard_upload_audio, name='dashboard_upload_audio'),
    path('analysis-status/<uuid:analysis_id>/', views.dashboard_analysis_status, name='dashboard_analysis_status'),
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('law-enforcement/', views.law_enforcement_dashboard_view, name='law_enforcement_dashboard'),
    path('law-enforcement/analysis/', views.law_enforcement_analysis_view, name='law_enforcement_analysis'),
]
