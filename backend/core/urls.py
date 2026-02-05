"""
Core URL configuration - Authentication endpoints.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from . import views

app_name = 'core'

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),

    # User profile
    path('me/', views.get_current_user, name='current_user'),
    path('profile/', views.update_profile, name='update_profile'),
    path('api-keys/', views.update_api_keys, name='update_api_keys'),
    path('skill-api-keys/', views.skill_api_keys, name='skill_api_keys'),
    path('change-password/', views.change_password, name='change_password'),
]
