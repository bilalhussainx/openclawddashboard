"""
URL configuration for OpenClaw Dashboard project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('core.urls')),
    path('api/workspaces/', include('workspaces.urls')),
    path('api/skills/', include('skills.urls')),
    path('api/billing/', include('billing.urls')),
    path('api/jobapply/', include('jobapply.urls')),
    path('api/google/', include('google_integration.urls')),
]
