"""
Automation URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from . import views

app_name = 'automations'

# Global tools endpoint
router = DefaultRouter()
router.register(r'tools', views.AgentToolViewSet, basename='tools')

urlpatterns = [
    path('', include(router.urls)),
]
