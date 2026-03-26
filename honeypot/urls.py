"""
URL patterns for Honeypot app
"""

from django.urls import path
from . import views

app_name = 'honeypot'

urlpatterns = [
    # Dashboard
    path('', views.honeypot_dashboard, name='honeypot_dashboard'),

    # Session management
    path('sessions/', views.honeypot_session_list, name='honeypot_session_list'),
    path('sessions/create/', views.honeypot_session_create, name='honeypot_session_create'),
    path('sessions/<uuid:session_id>/', views.honeypot_session_detail, name='honeypot_session_detail'),
    path('sessions/<uuid:session_id>/edit/', views.honeypot_session_edit, name='honeypot_session_edit'),
    path('sessions/<uuid:session_id>/toggle/', views.honeypot_session_toggle_status, name='honeypot_session_toggle_status'),

    # Interaction management
    path('interactions/<uuid:interaction_id>/', views.honeypot_interaction_detail, name='honeypot_interaction_detail'),
    path('sessions/<uuid:session_id>/interact/', views.honeypot_interaction_manual, name='honeypot_interaction_manual'),

    # Scammer profiles
    path('scammers/', views.scammer_profile_list, name='scammer_profile_list'),
    path('scammers/create/', views.scammer_profile_create, name='scammer_profile_create'),
    path('scammers/<uuid:profile_id>/', views.scammer_profile_detail, name='scammer_profile_detail'),
    path('scammers/<uuid:profile_id>/edit/', views.scammer_profile_edit, name='scammer_profile_edit'),

    # Reports
    path('reports/', views.honeypot_reports, name='honeypot_reports'),

    # API endpoints
    path('api/sessions/<uuid:session_id>/process/', views.api_process_call, name='api_process_call'),
    path('api/sessions/<uuid:session_id>/status/', views.api_session_status, name='api_session_status'),
]
