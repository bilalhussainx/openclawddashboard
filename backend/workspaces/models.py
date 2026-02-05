"""
Workspace models - Workspace, Channel, and InstalledSkill definitions.
"""
from django.db import models
from django.conf import settings


class Workspace(models.Model):
    """
    Represents a customer's OpenClaw deployment.
    Each workspace maps to an isolated Docker container.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DEPLOYING = 'deploying', 'Deploying'
        RUNNING = 'running', 'Running'
        STOPPED = 'stopped', 'Stopped'
        ERROR = 'error', 'Error'

    class ModelChoice(models.TextChoices):
        CLAUDE_OPUS = 'claude-opus-4-20250514', 'Claude Opus 4'
        CLAUDE_SONNET = 'claude-sonnet-4-20250514', 'Claude Sonnet 4'
        CLAUDE_HAIKU = 'claude-3-5-haiku-20241022', 'Claude 3.5 Haiku'
        GPT4 = 'gpt-4-turbo-preview', 'GPT-4 Turbo'
        GPT35 = 'gpt-3.5-turbo', 'GPT-3.5 Turbo'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspaces'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # AI Model Configuration
    selected_model = models.CharField(
        max_length=100,
        choices=ModelChoice.choices,
        default=ModelChoice.CLAUDE_SONNET
    )

    # Deployment Configuration
    assigned_port = models.IntegerField(unique=True, null=True, blank=True)
    container_id = models.CharField(max_length=100, blank=True)
    gateway_token = models.CharField(
        max_length=64,
        blank=True,
        help_text='Token for authenticating with the OpenClaw Gateway WebSocket'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    last_health_check = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Agent Configuration
    system_prompt = models.TextField(
        blank=True,
        default='You are a helpful AI assistant.',
        help_text='The system prompt that defines the agent behavior'
    )
    agent_name = models.CharField(
        max_length=100,
        blank=True,
        default='Assistant',
        help_text='The name the agent uses to identify itself'
    )
    agent_description = models.TextField(
        blank=True,
        help_text='Brief description of what this agent does'
    )
    welcome_message = models.TextField(
        blank=True,
        default='Hello! How can I help you today?',
        help_text='Message sent when a user first interacts'
    )

    # Agent Behavior Settings
    temperature = models.FloatField(
        default=0.7,
        help_text='Controls randomness (0.0 = deterministic, 1.0 = creative)'
    )

    # Settings
    sandbox_mode = models.BooleanField(
        default=True,
        help_text='Enable sandbox mode for safe execution'
    )
    max_tokens = models.IntegerField(default=4096)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

    def get_config_path(self):
        """Get the path to this workspace's OpenClaw config directory."""
        return f"{settings.OPENCLAW_DATA_PATH}/{self.id}"

    @property
    def is_running(self):
        return self.status == self.Status.RUNNING


class Channel(models.Model):
    """
    Represents a connected messaging channel (Telegram, Slack, etc.)
    """

    class ChannelType(models.TextChoices):
        TELEGRAM = 'telegram', 'Telegram'
        SLACK = 'slack', 'Slack'
        DISCORD = 'discord', 'Discord'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        TEAMS = 'teams', 'Microsoft Teams'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='channels'
    )
    channel_type = models.CharField(
        max_length=20,
        choices=ChannelType.choices
    )
    name = models.CharField(max_length=100)

    # Credentials (stored as JSON, should be encrypted in production)
    credentials = models.JSONField(
        default=dict,
        help_text='Channel-specific credentials and tokens'
    )

    # Allowlist for who can interact with the bot
    allowlist = models.JSONField(
        default=list,
        help_text='List of allowed users/groups/channels'
    )

    # Settings
    is_active = models.BooleanField(default=True)
    respond_to_groups = models.BooleanField(
        default=False,
        help_text='Whether to respond in group chats'
    )

    # OAuth state (for Slack, etc.)
    oauth_state = models.CharField(max_length=100, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['workspace', 'channel_type']
        verbose_name = 'Channel'
        verbose_name_plural = 'Channels'

    def __str__(self):
        return f"{self.get_channel_type_display()} - {self.workspace.name}"


class InstalledSkill(models.Model):
    """
    Represents a skill installed in a workspace.
    """

    class InstallStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        INSTALLING = 'installing', 'Installing'
        READY = 'ready', 'Ready'
        ERROR = 'error', 'Error'
        MISSING_REQUIREMENTS = 'missing_reqs', 'Missing Requirements'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='installed_skills'
    )
    skill = models.ForeignKey(
        'skills.Skill',
        on_delete=models.CASCADE,
        related_name='installations'
    )

    # Configuration
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(
        default=dict,
        help_text='Skill-specific configuration overrides'
    )

    # Installation status
    install_status = models.CharField(
        max_length=20,
        choices=InstallStatus.choices,
        default=InstallStatus.PENDING,
        help_text='Current installation status'
    )
    install_error = models.TextField(
        blank=True,
        help_text='Error message if installation failed'
    )
    clawhub_installed = models.BooleanField(
        default=False,
        help_text='Whether clawhub install was run in the container'
    )

    # Timestamps
    installed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-installed_at']
        unique_together = ['workspace', 'skill']
        verbose_name = 'Installed Skill'
        verbose_name_plural = 'Installed Skills'

    def __str__(self):
        return f"{self.skill.name} in {self.workspace.name}"


class KnowledgeBase(models.Model):
    """
    Represents a document or resource uploaded to a workspace's knowledge base.
    The agent can reference these when responding to users.
    """

    class ResourceType(models.TextChoices):
        DOCUMENT = 'document', 'Document'
        TEXT = 'text', 'Text Snippet'
        URL = 'url', 'Web URL'
        FAQ = 'faq', 'FAQ Entry'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='knowledge_base'
    )
    name = models.CharField(max_length=200)
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
        default=ResourceType.TEXT
    )

    # Content
    content = models.TextField(
        blank=True,
        help_text='Text content or extracted document text'
    )
    file = models.FileField(
        upload_to='knowledge_base/',
        blank=True,
        null=True,
        help_text='Uploaded document file'
    )
    source_url = models.URLField(
        blank=True,
        help_text='Source URL if this is a web resource'
    )

    # FAQ specific fields
    question = models.TextField(
        blank=True,
        help_text='Question (for FAQ type)'
    )
    answer = models.TextField(
        blank=True,
        help_text='Answer (for FAQ type)'
    )

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Knowledge Base Entry'
        verbose_name_plural = 'Knowledge Base Entries'

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"
