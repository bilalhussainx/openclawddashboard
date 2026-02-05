"""
Workspace admin configuration.
"""
from django.contrib import admin
from .models import Workspace, Channel, InstalledSkill


class ChannelInline(admin.TabularInline):
    model = Channel
    extra = 0
    readonly_fields = ['created_at']


class InstalledSkillInline(admin.TabularInline):
    model = InstalledSkill
    extra = 0
    readonly_fields = ['installed_at']


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'owner',
        'status',
        'selected_model',
        'assigned_port',
        'created_at',
    ]
    list_filter = ['status', 'selected_model', 'created_at']
    search_fields = ['name', 'owner__email']
    readonly_fields = ['container_id', 'assigned_port', 'last_health_check']
    inlines = [ChannelInline, InstalledSkillInline]


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = [
        'workspace',
        'channel_type',
        'name',
        'is_active',
        'created_at',
    ]
    list_filter = ['channel_type', 'is_active', 'created_at']
    search_fields = ['workspace__name', 'name']


@admin.register(InstalledSkill)
class InstalledSkillAdmin(admin.ModelAdmin):
    list_display = [
        'workspace',
        'skill',
        'is_enabled',
        'installed_at',
    ]
    list_filter = ['is_enabled', 'installed_at']
    search_fields = ['workspace__name', 'skill__name']
