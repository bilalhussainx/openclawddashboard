from rest_framework import serializers
from .models import Resume, JobPreferences, JobListing, JobApplication, DailyApplicationSummary


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = [
            'id', 'name', 'file', 'file_type', 'extracted_text',
            'parsed_data', 'is_primary', 'created_at', 'updated_at',
        ]
        read_only_fields = ['extracted_text', 'parsed_data', 'file_type', 'created_at', 'updated_at']


class JobPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPreferences
        fields = [
            'id', 'keywords', 'excluded_keywords', 'location', 'remote_ok',
            'salary_min', 'salary_max', 'enabled_boards',
            'auto_apply_enabled', 'auto_apply_min_score', 'max_daily_applications',
            'workspace', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class JobListingSerializer(serializers.ModelSerializer):
    has_application = serializers.SerializerMethodField()
    application_info = serializers.SerializerMethodField()

    class Meta:
        model = JobListing
        fields = [
            'id', 'title', 'company', 'location', 'url', 'description',
            'salary_info', 'job_type', 'source_board', 'match_score',
            'score_breakdown', 'matched_keywords', 'dismissed',
            'discovered_at', 'has_application', 'application_info',
        ]

    def get_has_application(self, obj):
        return obj.applications.exists()

    def get_application_info(self, obj):
        app = obj.applications.order_by('-created_at').first()
        if not app:
            return None
        return {
            'id': app.id,
            'status': app.status,
            'applied_via': app.applied_via,
            'error_message': app.error_message,
            'applied_at': app.applied_at.isoformat() if app.applied_at else None,
            'has_cover_letter': bool(app.cover_letter),
        }


class JobApplicationSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_company = serializers.CharField(source='listing.company', read_only=True)
    listing_url = serializers.URLField(source='listing.url', read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            'id', 'listing', 'listing_title', 'listing_company', 'listing_url',
            'resume', 'status', 'cover_letter', 'applied_at', 'applied_via',
            'error_message', 'automation_log', 'retry_count', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'cover_letter', 'applied_at', 'applied_via', 'error_message',
            'automation_log', 'retry_count', 'created_at', 'updated_at',
        ]


class DailyApplicationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyApplicationSummary
        fields = [
            'id', 'date', 'jobs_discovered', 'applications_sent',
            'applications_failed', 'high_score_jobs', 'summary_text', 'sent_at',
        ]


class DashboardSerializer(serializers.Serializer):
    total_listings = serializers.IntegerField()
    total_applications = serializers.IntegerField()
    applied_count = serializers.IntegerField()
    interview_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    avg_match_score = serializers.FloatField()
    recent_listings = JobListingSerializer(many=True)
    recent_applications = JobApplicationSerializer(many=True)
