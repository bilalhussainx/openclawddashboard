"""
Skills URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'skills'

router = DefaultRouter()
router.register(r'', views.SkillViewSet, basename='skill')

urlpatterns = [
    path('', include(router.urls)),
]
