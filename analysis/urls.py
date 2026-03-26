from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    # AI Analysis management
    path('', views.analysis_list_view, name='analysis_list'),
    path('<uuid:analysis_id>/', views.analysis_detail_view, name='analysis_detail'),
    path('request/<uuid:call_id>/', views.request_analysis_view, name='request_analysis'),

    # Scam scores
    path('scores/', views.scam_scores_view, name='scam_scores'),
    path('scores/<uuid:score_id>/review/', views.review_scam_score_view, name='review_scam_score'),

    # Statistics and analytics
    path('statistics/', views.analysis_statistics_view, name='analysis_statistics'),

    # API endpoints
    path('api/status/<uuid:analysis_id>/', views.api_analysis_status, name='api_analysis_status'),
]
