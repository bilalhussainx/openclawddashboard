"""
Workspace views - API endpoints for workspace management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Workspace, Channel, InstalledSkill, KnowledgeBase
from .serializers import (
    WorkspaceSerializer,
    WorkspaceCreateSerializer,
    ChannelSerializer,
    ChannelCreateSerializer,
    InstalledSkillSerializer,
    KnowledgeBaseSerializer,
    AgentConfigSerializer,
)
from .tasks import deploy_workspace, stop_workspace, get_workspace_logs


class WorkspaceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Workspace CRUD operations.

    list: GET /api/workspaces/
    create: POST /api/workspaces/
    retrieve: GET /api/workspaces/{id}/
    update: PUT /api/workspaces/{id}/
    partial_update: PATCH /api/workspaces/{id}/
    destroy: DELETE /api/workspaces/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Workspace.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return WorkspaceCreateSerializer
        return WorkspaceSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        """
        Deploy the workspace (start OpenClaw container).

        POST /api/workspaces/{id}/deploy/
        """
        workspace = self.get_object()

        if workspace.status == Workspace.Status.RUNNING:
            return Response(
                {'error': 'Workspace is already running'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if workspace.status == Workspace.Status.DEPLOYING:
            return Response(
                {'error': 'Workspace is already deploying'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has API key set
        if not request.user.anthropic_api_key and not request.user.openai_api_key:
            return Response(
                {'error': 'Please configure an API key before deploying'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status and trigger deployment
        workspace.status = Workspace.Status.DEPLOYING
        workspace.error_message = ''
        workspace.save()

        # Trigger async deployment task
        deploy_workspace.delay(workspace.id)

        return Response({
            'message': 'Deployment started',
            'status': workspace.status,
        })

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """
        Stop the workspace (stop OpenClaw container).

        POST /api/workspaces/{id}/stop/
        """
        workspace = self.get_object()

        if workspace.status not in [Workspace.Status.RUNNING, Workspace.Status.ERROR]:
            return Response(
                {'error': 'Workspace is not running'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Trigger async stop task
        stop_workspace.delay(workspace.id)

        return Response({
            'message': 'Stop command sent',
            'status': workspace.status,
        })

    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """
        Get detailed workspace status.

        GET /api/workspaces/{id}/status/
        """
        workspace = self.get_object()

        uptime = None
        if workspace.status == Workspace.Status.RUNNING and workspace.last_health_check:
            uptime = (timezone.now() - workspace.created_at).total_seconds()

        return Response({
            'status': workspace.status,
            'status_display': workspace.get_status_display(),
            'is_running': workspace.is_running,
            'container_id': workspace.container_id,
            'last_health_check': workspace.last_health_check,
            'error_message': workspace.error_message,
            'uptime_seconds': uptime,
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        Get container logs for the workspace.

        GET /api/workspaces/{id}/logs/
        """
        workspace = self.get_object()

        if not workspace.container_id:
            return Response(
                {'error': 'No container found for this workspace'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get logs (this could be async for large logs)
        lines = int(request.query_params.get('lines', 100))
        logs = get_workspace_logs(workspace.id, lines=lines)

        return Response({
            'container_id': workspace.container_id,
            'logs': logs,
        })

    @action(detail=True, methods=['get', 'put', 'patch'])
    def agent_config(self, request, pk=None):
        """
        Get or update agent configuration.

        GET /api/workspaces/{id}/agent_config/
        PUT/PATCH /api/workspaces/{id}/agent_config/
        """
        workspace = self.get_object()

        if request.method == 'GET':
            serializer = AgentConfigSerializer(workspace)
            return Response(serializer.data)

        serializer = AgentConfigSerializer(
            workspace,
            data=request.data,
            partial=(request.method == 'PATCH')
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def skill_status(self, request, pk=None):
        """
        Get installed skills with their status.

        GET /api/workspaces/{id}/skill_status/
        """
        workspace = self.get_object()
        installed_skills = workspace.installed_skills.select_related('skill').all()

        skills_data = []
        for installed in installed_skills:
            skill = installed.skill

            # Check for missing requirements
            missing_env = []
            user_skill_keys = getattr(request.user, 'skill_api_keys', None) or {}
            required_env = skill.required_env or []

            for env_var in required_env:
                if env_var not in user_skill_keys:
                    if env_var == 'ANTHROPIC_API_KEY' and request.user.anthropic_api_key:
                        continue
                    if env_var == 'OPENAI_API_KEY' and request.user.openai_api_key:
                        continue
                    missing_env.append(env_var)

            skills_data.append({
                'id': installed.id,
                'skill_slug': skill.slug,
                'skill_name': skill.name,
                'skill_icon': skill.icon_url,
                'is_enabled': installed.is_enabled,
                'install_status': installed.install_status,
                'install_status_display': installed.get_install_status_display(),
                'install_error': installed.install_error,
                'clawhub_installed': installed.clawhub_installed,
                'installed_at': installed.installed_at,
                'missing_requirements': missing_env,
                'required_env': required_env,
            })

        return Response({
            'workspace_id': workspace.id,
            'workspace_name': workspace.name,
            'skills': skills_data,
            'total_count': len(skills_data),
            'ready_count': sum(1 for s in skills_data if s['install_status'] == 'ready'),
        })

    @action(detail=True, methods=['post'])
    def test_message(self, request, pk=None):
        """
        Send a test message to the agent (for preview/testing).

        POST /api/workspaces/{id}/test_message/
        """
        workspace = self.get_object()
        message = request.data.get('message', '')

        if not message:
            return Response(
                {'error': 'message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get user's API key
        api_key = request.user.anthropic_api_key or request.user.openai_api_key
        if not api_key:
            return Response(
                {'error': 'Please configure an API key first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build context from knowledge base
        knowledge_context = ""
        kb_entries = workspace.knowledge_base.filter(is_active=True)
        if kb_entries.exists():
            knowledge_context = "\n\n## Knowledge Base:\n"
            for entry in kb_entries[:10]:  # Limit to 10 entries for context
                if entry.resource_type == 'faq':
                    knowledge_context += f"\nQ: {entry.question}\nA: {entry.answer}\n"
                elif entry.content:
                    knowledge_context += f"\n### {entry.name}:\n{entry.content[:2000]}\n"

        # Build the full system prompt
        full_system = workspace.system_prompt
        if knowledge_context:
            full_system += knowledge_context

        # Call the AI API
        try:
            if request.user.anthropic_api_key:
                import anthropic
                client = anthropic.Anthropic(api_key=request.user.anthropic_api_key)
                response = client.messages.create(
                    model=workspace.selected_model,
                    max_tokens=workspace.max_tokens,
                    system=full_system,
                    messages=[{"role": "user", "content": message}]
                )
                reply = response.content[0].text
            else:
                from openai import OpenAI
                client = OpenAI(api_key=request.user.openai_api_key)
                response = client.chat.completions.create(
                    model=workspace.selected_model,
                    max_tokens=workspace.max_tokens,
                    messages=[
                        {"role": "system", "content": full_system},
                        {"role": "user", "content": message}
                    ]
                )
                reply = response.choices[0].message.content

            return Response({
                'message': message,
                'reply': reply,
                'model': workspace.selected_model,
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChannelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Channel CRUD operations within a workspace.

    list: GET /api/workspaces/{workspace_id}/channels/
    create: POST /api/workspaces/{workspace_id}/channels/
    retrieve: GET /api/workspaces/{workspace_id}/channels/{id}/
    update: PUT /api/workspaces/{workspace_id}/channels/{id}/
    destroy: DELETE /api/workspaces/{workspace_id}/channels/{id}/
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
        return Channel.objects.filter(workspace=workspace)

    def get_serializer_class(self):
        if self.action == 'create':
            return ChannelCreateSerializer
        return ChannelSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create':
            context['workspace'] = self.get_workspace()
        return context

    def perform_create(self, serializer):
        workspace = self.get_workspace()
        serializer.save(workspace=workspace)

    @action(detail=False, methods=['post'], url_path='slack/oauth')
    def slack_oauth_init(self, request, workspace_pk=None):
        """
        Initialize Slack OAuth flow.

        POST /api/workspaces/{workspace_id}/channels/slack/oauth/
        """
        workspace = self.get_workspace()

        # Generate OAuth state
        import secrets
        state = secrets.token_urlsafe(32)

        # Store state temporarily (could use Redis/cache in production)
        channel, created = Channel.objects.get_or_create(
            workspace=workspace,
            channel_type=Channel.ChannelType.SLACK,
            defaults={'name': 'Slack', 'is_active': False}
        )
        channel.oauth_state = state
        channel.save()

        from django.conf import settings
        oauth_url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={settings.SLACK_CLIENT_ID}"
            f"&scope=chat:write,channels:history,groups:history,im:history,mpim:history"
            f"&redirect_uri={settings.SLACK_REDIRECT_URI}"
            f"&state={state}"
        )

        return Response({'oauth_url': oauth_url})

    @action(detail=False, methods=['post'], url_path='telegram/setup')
    def telegram_setup(self, request, workspace_pk=None):
        """
        Set up Telegram bot channel.

        POST /api/workspaces/{workspace_id}/channels/telegram/setup/
        """
        workspace = self.get_workspace()
        bot_token = request.data.get('bot_token')

        if not bot_token:
            return Response(
                {'error': 'bot_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        channel, created = Channel.objects.get_or_create(
            workspace=workspace,
            channel_type=Channel.ChannelType.TELEGRAM,
            defaults={'name': 'Telegram'}
        )

        channel.credentials = {'bot_token': bot_token}
        channel.is_active = True
        channel.save()

        return Response({
            'message': 'Telegram channel configured successfully',
            'channel': ChannelSerializer(channel).data,
        })


class InstalledSkillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for InstalledSkill operations within a workspace.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InstalledSkillSerializer

    def get_workspace(self):
        workspace_id = self.kwargs.get('workspace_pk')
        return get_object_or_404(
            Workspace,
            id=workspace_id,
            owner=self.request.user
        )

    def get_queryset(self):
        workspace = self.get_workspace()
        return InstalledSkill.objects.filter(workspace=workspace)

    def perform_create(self, serializer):
        workspace = self.get_workspace()
        serializer.save(workspace=workspace)


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for KnowledgeBase CRUD operations within a workspace.

    list: GET /api/workspaces/{workspace_id}/knowledge/
    create: POST /api/workspaces/{workspace_id}/knowledge/
    retrieve: GET /api/workspaces/{workspace_id}/knowledge/{id}/
    update: PUT /api/workspaces/{workspace_id}/knowledge/{id}/
    destroy: DELETE /api/workspaces/{workspace_id}/knowledge/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = KnowledgeBaseSerializer

    def get_workspace(self):
        workspace_id = self.kwargs.get('workspace_pk')
        return get_object_or_404(
            Workspace,
            id=workspace_id,
            owner=self.request.user
        )

    def get_queryset(self):
        workspace = self.get_workspace()
        return KnowledgeBase.objects.filter(workspace=workspace)

    def perform_create(self, serializer):
        workspace = self.get_workspace()
        serializer.save(workspace=workspace)
