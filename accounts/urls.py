from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('system/register/', views.system_register_view, name='system_register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('setup_otp/', views.setup_otp_view, name='setup_otp'),
    path('otp_login/', views.otp_login_view, name='otp_login'),
    path('manage_2fa/', views.manage_2fa_view, name='manage_2fa'),
    path('remove_2fa_device/<int:device_id>/', views.remove_2fa_device_view, name='remove_2fa_device'),
    path('disable_2fa/', views.disable_2fa_view, name='disable_2fa'),
    path('add_2fa_device/', views.manage_2fa_view, name='add_2fa_device'),
]
