"""
Agent Task serializers.
"""
from rest_framework import serializers
from .models import AgentTask, AgentTool, TaskRun, TaskResult


class AgentToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTool
        fields = [
            'id', 'name', 'slug', 'description', 'tool_type',
            'config_schema', 'is_active',
        ]


class TaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResult
        fields = [
            'id', 'result_type', 'title', 'data', 'url', 'score', 'summary',
            'is_new', 'is_sent', 'is_saved', 'user_rating', 'user_notes',
            'found_at',
        ]


class TaskRunSerializer(serializers.ModelSerializer):
    structured_results = TaskResultSerializer(many=True, read_only=True)

    class Meta:
        model = TaskRun
        fields = [
            'id', 'started_at', 'completed_at', 'status',
            'agent_reasoning', 'tools_used', 'steps_taken',
            'result', 'result_data', 'error_message', 'tokens_used',
            'structured_results',
        ]


class AgentTaskSerializer(serializers.ModelSerializer):
    recent_results = serializers.SerializerMethodField()
    result_count = serializers.SerializerMethodField()
    high_score_count = serializers.SerializerMethodField()
    last_run_info = serializers.SerializerMethodField()
    available_tools = serializers.SerializerMethodField()

    class Meta:
        model = AgentTask
        fields = [
            'id', 'name', 'instructions', 'enabled_tools', 'schedule', 'status',
            'last_run', 'next_run', 'run_count', 'last_result', 'last_error',
            'recent_results', 'result_count', 'high_score_count', 'last_run_info', 'available_tools',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'last_run', 'next_run', 'run_count', 'created_at', 'updated_at']

    def get_recent_results(self, obj):
        # Return most recent results (both saved and unsaved) ordered by score then date
        results = obj.results.order_by('-score', '-found_at')[:5]
        return TaskResultSerializer(results, many=True).data

    def get_result_count(self, obj):
        return obj.results.count()

    def get_high_score_count(self, obj):
        return obj.results.filter(score__gte=70).count()

    def get_last_run_info(self, obj):
        last_run = obj.runs.first()
        if last_run:
            return TaskRunSerializer(last_run).data
        return None

    def get_available_tools(self, obj):
        tools = AgentTool.objects.filter(is_active=True, is_global=True)
        return AgentToolSerializer(tools, many=True).data


class AgentTaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTask
        fields = ['name', 'instructions', 'enabled_tools', 'schedule']
