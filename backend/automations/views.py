"""
Agent Task views - API endpoints for agent task management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from workspaces.models import Workspace
from .models import AgentTask, AgentTool, TaskRun, TaskResult
from .serializers import (
    AgentTaskSerializer,
    AgentTaskCreateSerializer,
    AgentToolSerializer,
    TaskRunSerializer,
    TaskResultSerializer,
)
from .tasks import execute_agent_task


class AgentToolViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing available agent tools.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AgentToolSerializer
    queryset = AgentTool.objects.filter(is_active=True)


class AgentTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Agent Task CRUD and execution.
    """
    permission_classes = [IsAuthenticated]

    def get_workspace(self):
        workspace_id = self.kwargs.get('workspace_pk')
        return get_object_or_404(
            Workspace,
            id=workspace_id,
            owner=self.request.user
        )

    def get_queryset(self):
        workspace = self.get_workspace()
        return AgentTask.objects.filter(workspace=workspace)

    def get_serializer_class(self):
        if self.action == 'create':
            return AgentTaskCreateSerializer
        return AgentTaskSerializer

    def perform_create(self, serializer):
        workspace = self.get_workspace()
        serializer.save(workspace=workspace)

    @action(detail=True, methods=['post'])
    def run(self, request, workspace_pk=None, pk=None):
        """
        Execute the task now.
        """
        task = self.get_object()

        # Check if workspace owner has API key
        workspace = task.workspace
        if not workspace.owner.anthropic_api_key and not workspace.owner.openai_api_key:
            return Response(
                {'error': 'Please configure an API key first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Trigger async task execution
        execute_agent_task.delay(task.id)

        return Response({
            'message': 'Task execution started',
            'task_id': task.id,
        })

    @action(detail=True, methods=['post'])
    def pause(self, request, workspace_pk=None, pk=None):
        """Pause a scheduled task."""
        task = self.get_object()
        task.status = AgentTask.Status.PAUSED
        task.save()
        return Response({'status': task.status})

    @action(detail=True, methods=['post'])
    def resume(self, request, workspace_pk=None, pk=None):
        """Resume a paused task."""
        task = self.get_object()
        task.status = AgentTask.Status.PENDING
        task.save()
        return Response({'status': task.status})

    @action(detail=True, methods=['get'])
    def results(self, request, workspace_pk=None, pk=None):
        """
        Get all results from this task.
        """
        task = self.get_object()
        results = task.results.all()

        # Filters
        is_saved = request.query_params.get('is_saved')
        if is_saved == 'true':
            results = results.filter(is_saved=True)

        result_type = request.query_params.get('type')
        if result_type:
            results = results.filter(result_type=result_type)

        return Response({
            'total': results.count(),
            'results': TaskResultSerializer(results[:100], many=True).data,
        })

    @action(detail=True, methods=['get'])
    def runs(self, request, workspace_pk=None, pk=None):
        """
        Get execution history.
        """
        task = self.get_object()
        runs = task.runs.all()[:20]
        return Response(TaskRunSerializer(runs, many=True).data)


class TaskResultViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing task results.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TaskResultSerializer

    def get_task(self):
        workspace_id = self.kwargs.get('workspace_pk')
        task_id = self.kwargs.get('task_pk')
        workspace = get_object_or_404(
            Workspace,
            id=workspace_id,
            owner=self.request.user
        )
        return get_object_or_404(
            AgentTask,
            id=task_id,
            workspace=workspace
        )

    def get_queryset(self):
        task = self.get_task()
        return TaskResult.objects.filter(task=task)

    @action(detail=True, methods=['post'])
    def save(self, request, **kwargs):
        """Save a result."""
        result = self.get_object()
        result.is_saved = True
        result.save()
        return Response({'is_saved': True})

    @action(detail=True, methods=['post'])
    def rate(self, request, **kwargs):
        """Rate a result."""
        result = self.get_object()
        result.user_rating = request.data.get('rating')
        result.save()
        return Response({'user_rating': result.user_rating})
