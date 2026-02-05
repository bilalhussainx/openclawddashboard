"""
Agent Tasks - Let users define tasks for their AI agent to accomplish.
"""
from django.db import models
from django.conf import settings


class AgentTask(models.Model):
    """
    A task/goal the user wants the agent to accomplish.
    The agent uses its tools and capabilities to complete the task.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        PAUSED = 'paused', 'Paused'

    class Schedule(models.TextChoices):
        ONCE = 'once', 'Run Once'
        HOURLY = 'hourly', 'Every Hour'
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'

    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='agent_tasks'
    )

    # Task definition (natural language)
    name = models.CharField(max_length=200)
    instructions = models.TextField(
        help_text='Natural language instructions for what the agent should do'
    )

    # Example instructions the user might give:
    # "Search LinkedIn and Indeed for jobs with titles containing 'AI Engineer',
    #  'ML Engineer', or 'Claude'. Score each job based on how well it matches
    #  these keywords: 'remote', 'startup', 'LLM', 'Python'. Send me the top 10
    #  matches daily via Telegram with the job title, company, link, and your score."

    # Tools the agent can use for this task
    enabled_tools = models.JSONField(
        default=list,
        help_text='List of tool IDs the agent can use'
    )

    # Schedule
    schedule = models.CharField(
        max_length=20,
        choices=Schedule.choices,
        default=Schedule.ONCE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Execution tracking
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    run_count = models.IntegerField(default=0)

    # Results storage
    last_result = models.TextField(blank=True)
    last_error = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"


class AgentTool(models.Model):
    """
    A tool/capability that agents can use to accomplish tasks.
    """

    class ToolType(models.TextChoices):
        WEB_SEARCH = 'web_search', 'Web Search'
        WEB_SCRAPE = 'web_scrape', 'Web Scraper'
        API_CALL = 'api_call', 'API Call'
        FILE_READ = 'file_read', 'File Reader'
        SEND_MESSAGE = 'send_message', 'Send Message'
        CODE_EXECUTE = 'code_execute', 'Code Executor'

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    tool_type = models.CharField(
        max_length=50,
        choices=ToolType.choices
    )

    # Tool configuration schema (JSON Schema)
    config_schema = models.JSONField(
        default=dict,
        help_text='JSON Schema for tool configuration'
    )

    # Is this tool available to all workspaces?
    is_global = models.BooleanField(default=True)

    # Tool implementation details
    implementation = models.JSONField(
        default=dict,
        help_text='Implementation details (endpoint, code, etc.)'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TaskRun(models.Model):
    """
    Record of a task execution.
    """
    task = models.ForeignKey(
        AgentTask,
        on_delete=models.CASCADE,
        related_name='runs'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50)

    # What the agent did
    agent_reasoning = models.TextField(blank=True)
    tools_used = models.JSONField(default=list)
    steps_taken = models.JSONField(default=list)

    # Results
    result = models.TextField(blank=True)
    result_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    # Tokens used (for billing)
    tokens_used = models.IntegerField(default=0)

    class Meta:
        ordering = ['-started_at']


class TaskResult(models.Model):
    """
    Structured result from a task (e.g., a job listing, a scraped item).
    """
    task = models.ForeignKey(
        AgentTask,
        on_delete=models.CASCADE,
        related_name='results'
    )
    run = models.ForeignKey(
        TaskRun,
        on_delete=models.CASCADE,
        related_name='structured_results',
        null=True
    )

    # Result type and data
    result_type = models.CharField(max_length=100)  # job, article, product, etc.
    title = models.CharField(max_length=500)
    data = models.JSONField(default=dict)  # Flexible storage for any result type

    # Common fields
    url = models.URLField(max_length=2000, blank=True)
    score = models.FloatField(null=True, blank=True)
    summary = models.TextField(blank=True)

    # Status
    is_new = models.BooleanField(default=True)
    is_sent = models.BooleanField(default=False)
    is_saved = models.BooleanField(default=False)

    # User interaction
    user_rating = models.IntegerField(null=True, blank=True)
    user_notes = models.TextField(blank=True)

    found_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score', '-found_at']

    def __str__(self):
        return f"{self.result_type}: {self.title}"
