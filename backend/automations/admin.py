from django.contrib import admin
from .models import AgentTask, AgentTool, TaskRun, TaskResult


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'workspace', 'status', 'schedule', 'run_count', 'last_run']
    list_filter = ['status', 'schedule']
    search_fields = ['name', 'instructions']


@admin.register(AgentTool)
class AgentToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'tool_type', 'is_active', 'is_global']
    list_filter = ['tool_type', 'is_active']


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    list_display = ['task', 'status', 'started_at', 'completed_at', 'tokens_used']
    list_filter = ['status']


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ['title', 'result_type', 'task', 'score', 'is_saved', 'found_at']
    list_filter = ['result_type', 'is_saved']
    search_fields = ['title']
