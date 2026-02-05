"""
Workspace serializers - Workspace, Channel, and InstalledSkill serialization.
"""
from rest_framework import serializers
from .models import Workspace, Channel, InstalledSkill, KnowledgeBase


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer for Channel model."""
    channel_type_display = serializers.CharField(
        source='get_channel_type_display',
        read_only=True
    )

    class Meta:
        model = Channel
        fields = [
            'id',
            'channel_type',
            'channel_type_display',
            'name',
            'allowlist',
            'is_active',
            'respond_to_groups',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChannelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating channels with credentials."""

    class Meta:
        model = Channel
        fields = [
            'channel_type',
            'name',
            'credentials',
            'allowlist',
            'is_active',
            'respond_to_groups',
        ]

    def validate_channel_type(self, value):
        workspace = self.context.get('workspace')
        if workspace and Channel.objects.filter(
            workspace=workspace,
            channel_type=value
        ).exists():
            raise serializers.ValidationError(
                f'A {value} channel already exists for this workspace.'
            )
        return value


class InstalledSkillSerializer(serializers.ModelSerializer):
    """Serializer for InstalledSkill model."""
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_slug = serializers.CharField(source='skill.slug', read_only=True)

    class Meta:
        model = InstalledSkill
        fields = [
            'id',
            'skill',
            'skill_name',
            'skill_slug',
            'is_enabled',
            'config',
            'installed_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'installed_at', 'updated_at']


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """Serializer for KnowledgeBase model."""
    resource_type_display = serializers.CharField(
        source='get_resource_type_display',
        read_only=True
    )

    class Meta:
        model = KnowledgeBase
        fields = [
            'id',
            'name',
            'resource_type',
            'resource_type_display',
            'content',
            'file',
            'source_url',
            'question',
            'answer',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace model."""
    channels = ChannelSerializer(many=True, read_only=True)
    installed_skills = InstalledSkillSerializer(many=True, read_only=True)
    knowledge_base = KnowledgeBaseSerializer(many=True, read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    model_display = serializers.CharField(
        source='get_selected_model_display',
        read_only=True
    )
    is_running = serializers.BooleanField(read_only=True)

    class Meta:
        model = Workspace
        fields = [
            'id',
            'name',
            'description',
            'selected_model',
            'model_display',
            'assigned_port',
            'status',
            'status_display',
            'is_running',
            'last_health_check',
            'error_message',
            # Agent Configuration
            'system_prompt',
            'agent_name',
            'agent_description',
            'welcome_message',
            'temperature',
            # Settings
            'sandbox_mode',
            'max_tokens',
            # Related
            'channels',
            'installed_skills',
            'knowledge_base',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'assigned_port',
            'status',
            'container_id',
            'last_health_check',
            'error_message',
            'created_at',
            'updated_at',
        ]


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workspaces."""

    class Meta:
        model = Workspace
        fields = [
            'name',
            'description',
            'selected_model',
            'system_prompt',
            'agent_name',
            'agent_description',
            'welcome_message',
            'temperature',
            'sandbox_mode',
            'max_tokens',
        ]


class AgentConfigSerializer(serializers.ModelSerializer):
    """Serializer for updating agent configuration."""

    class Meta:
        model = Workspace
        fields = [
            'system_prompt',
            'agent_name',
            'agent_description',
            'welcome_message',
            'temperature',
            'selected_model',
            'max_tokens',
        ]


class WorkspaceDeploySerializer(serializers.Serializer):
    """Serializer for workspace deployment request."""
    pass  # No additional fields needed, just triggers deployment


class WorkspaceStatusSerializer(serializers.Serializer):
    """Serializer for workspace status response."""
    status = serializers.CharField()
    status_display = serializers.CharField()
    is_running = serializers.BooleanField()
    container_id = serializers.CharField(allow_blank=True)
    last_health_check = serializers.DateTimeField(allow_null=True)
    error_message = serializers.CharField(allow_blank=True)
    uptime_seconds = serializers.IntegerField(allow_null=True)
