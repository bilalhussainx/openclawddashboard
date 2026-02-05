"""
Workspace URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from . import views
from automations.views import AgentTaskViewSet, TaskResultViewSet

app_name = 'workspaces'

# Main router for workspaces
router = DefaultRouter()
router.register(r'', views.WorkspaceViewSet, basename='workspace')

# Nested router for channels within workspaces
workspace_router = routers.NestedDefaultRouter(router, r'', lookup='workspace')
workspace_router.register(r'channels', views.ChannelViewSet, basename='workspace-channels')
workspace_router.register(r'skills', views.InstalledSkillViewSet, basename='workspace-skills')
workspace_router.register(r'knowledge', views.KnowledgeBaseViewSet, basename='workspace-knowledge')
workspace_router.register(r'tasks', AgentTaskViewSet, basename='workspace-tasks')

# Nested router for task results
task_router = routers.NestedDefaultRouter(workspace_router, r'tasks', lookup='task')
task_router.register(r'results', TaskResultViewSet, basename='task-results')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(workspace_router.urls)),
    path('', include(task_router.urls)),
]
