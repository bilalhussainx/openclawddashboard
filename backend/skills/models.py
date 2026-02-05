"""
Skills models - Marketplace for OpenClaw skills from ClawHub.
"""
from django.db import models
from django.conf import settings


class Skill(models.Model):
    """
    Represents a skill available in the marketplace.
    Skills are sourced from ClawHub (clawhub.ai).
    """

    class Category(models.TextChoices):
        PRODUCTIVITY = 'productivity', 'Productivity'
        DEVELOPMENT = 'development', 'Development'
        DATA = 'data', 'Data & Analytics'
        COMMUNICATION = 'communication', 'Communication'
        AUTOMATION = 'automation', 'Automation'
        FUN = 'fun', 'Fun & Entertainment'
        OTHER = 'other', 'Other'

    # Basic info
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=200, blank=True)

    # Author/Source
    author = models.CharField(max_length=100)
    author_url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)

    # Presentation
    icon_url = models.URLField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER
    )
    tags = models.JSONField(default=list)

    # ClawHub integration
    clawhub_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    version = models.CharField(max_length=100, default='1.0.0')

    # Stats
    install_count = models.IntegerField(default=0)
    is_official = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Content (SKILL.md)
    skill_content = models.TextField(
        blank=True,
        help_text='SKILL.md content for this skill'
    )

    # Requirements
    required_tools = models.JSONField(
        default=list,
        help_text='List of tools this skill requires'
    )
    required_env = models.JSONField(
        default=list,
        help_text='Environment variables required'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-install_count', 'name']
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'

    def __str__(self):
        return f"{self.name} ({self.slug})"


class SkillRating(models.Model):
    """User rating for a skill."""
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['skill', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} rated {self.skill.name}: {self.rating}"
