"""
Job Auto-Apply models - automated job search, cover letter generation, and application submission.
"""
import hashlib
from django.db import models
from django.conf import settings


class Resume(models.Model):
    """User's uploaded resume with AI-extracted structured data."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resumes'
    )
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='resumes/')
    file_type = models.CharField(max_length=10, default='pdf')

    # Extracted content
    extracted_text = models.TextField(
        blank=True,
        help_text='Raw text extracted from PDF/DOCX'
    )
    parsed_data = models.JSONField(
        default=dict,
        help_text='Claude-parsed: {name, email, phone, location, summary, skills[], experience[], education[]}'
    )

    is_primary = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.name} ({'primary' if self.is_primary else 'alt'})"


class JobPreferences(models.Model):
    """User's job search configuration and auto-apply settings."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_preferences'
    )

    # Search criteria
    keywords = models.JSONField(
        default=list,
        help_text='Search keywords: ["Django Developer", "Full Stack", "React"]'
    )
    excluded_keywords = models.JSONField(
        default=list,
        help_text='Exclude jobs with: ["C++", "Director", ".NET"]'
    )
    location = models.CharField(max_length=200, default='Toronto')
    remote_ok = models.BooleanField(default=True)

    # Salary (CAD)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)

    # Job boards
    enabled_boards = models.JSONField(
        default=list,
        help_text='["linkedin", "indeed", "glassdoor"]'
    )

    # Auto-apply settings
    auto_apply_enabled = models.BooleanField(default=False)
    auto_apply_min_score = models.IntegerField(
        default=70,
        help_text='Only auto-apply to jobs scoring >= this'
    )
    max_daily_applications = models.IntegerField(default=10)

    # Linked workspace for OpenClaw browser automation
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text='Workspace whose OpenClaw container handles browser automation'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.email}: {self.location}"


class JobListing(models.Model):
    """A discovered job listing with match scoring."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_listings'
    )

    # Job data
    title = models.CharField(max_length=500)
    company = models.CharField(max_length=300)
    location = models.CharField(max_length=300, blank=True)
    url = models.URLField(max_length=2000)
    description = models.TextField(blank=True)
    salary_info = models.CharField(max_length=200, blank=True)
    job_type = models.CharField(max_length=50, blank=True)

    # Source
    source_board = models.CharField(max_length=50)
    external_id = models.CharField(max_length=200, blank=True)

    # Scoring
    match_score = models.IntegerField(default=0)
    score_breakdown = models.JSONField(default=dict)
    matched_keywords = models.JSONField(default=list)

    # Dedup
    url_hash = models.CharField(max_length=64, db_index=True)

    # Status
    dismissed = models.BooleanField(default=False)
    discovered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-match_score', '-discovered_at']
        unique_together = ['user', 'url_hash']

    def save(self, *args, **kwargs):
        if not self.url_hash:
            self.url_hash = hashlib.sha256(self.url.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} @ {self.company} (score: {self.match_score})"


class JobApplication(models.Model):
    """Tracks the full lifecycle of a job application."""

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        GENERATING_COVER = 'generating_cover', 'Generating Cover Letter'
        APPLYING = 'applying', 'Applying'
        APPLIED = 'applied', 'Applied'
        FAILED = 'failed', 'Failed'
        REJECTED = 'rejected', 'Rejected'
        INTERVIEW = 'interview', 'Interview'
        OFFER = 'offer', 'Offer'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    listing = models.ForeignKey(
        JobListing,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    resume = models.ForeignKey(
        Resume,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    # Application data
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.QUEUED
    )
    cover_letter = models.TextField(blank=True)

    # Execution tracking
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_via = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    # Browser automation log
    automation_log = models.JSONField(
        default=list,
        help_text='Step-by-step browser actions: [{step, action, ref, result}]'
    )

    # User notes
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'listing']

    def __str__(self):
        return f"{self.listing.title} - {self.status}"


class DailyApplicationSummary(models.Model):
    """Daily summary of automated job search and application activity."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='application_summaries'
    )
    date = models.DateField()
    jobs_discovered = models.IntegerField(default=0)
    applications_sent = models.IntegerField(default=0)
    applications_failed = models.IntegerField(default=0)
    high_score_jobs = models.IntegerField(default=0)
    summary_text = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.email} - {self.date}: {self.applications_sent} applied"
