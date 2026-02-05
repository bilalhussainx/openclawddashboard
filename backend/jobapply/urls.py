from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'jobapply'

router = DefaultRouter()
router.register(r'resumes', views.ResumeViewSet, basename='resumes')
router.register(r'listings', views.JobListingViewSet, basename='listings')
router.register(r'applications', views.JobApplicationViewSet, basename='applications')

urlpatterns = [
    path('preferences/', views.JobPreferencesView.as_view(), name='preferences'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('', include(router.urls)),
]
