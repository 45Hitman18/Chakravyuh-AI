from django.urls import path
from . import views

app_name = 'calls'

urlpatterns = [
    # Call listing and management
    path('', views.call_list_view, name='call_list'),
    path('create/', views.create_call_view, name='create_call'),
    path('<uuid:call_id>/', views.call_detail_view, name='call_detail'),
    path('<uuid:call_id>/upload-audio/', views.upload_audio_view, name='upload_audio'),

    # Statistics and analytics
    path('statistics/', views.call_statistics_view, name='call_statistics'),

    # API endpoints
    path('api/calls/', views.api_call_list, name='api_call_list'),
]
