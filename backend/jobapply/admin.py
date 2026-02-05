from django.contrib import admin
from .models import Resume, JobPreferences, JobListing, JobApplication, DailyApplicationSummary


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_primary', 'file_type', 'created_at']
    list_filter = ['is_primary', 'file_type']


@admin.register(JobPreferences)
class JobPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'location', 'auto_apply_enabled', 'max_daily_applications']


@admin.register(JobListing)
class JobListingAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'source_board', 'match_score', 'discovered_at']
    list_filter = ['source_board', 'dismissed']
    search_fields = ['title', 'company']


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['listing', 'status', 'applied_at', 'retry_count', 'created_at']
    list_filter = ['status']


@admin.register(DailyApplicationSummary)
class DailyApplicationSummaryAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'jobs_discovered', 'applications_sent', 'applications_failed']
