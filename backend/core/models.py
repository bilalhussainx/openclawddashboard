"""
Core models - Custom User model with email-based authentication.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with email as the primary identifier.
    Stores API keys for AI providers.
    """
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)

    # AI Provider API Keys (encrypted in production)
    anthropic_api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text='Anthropic API key for Claude models'
    )
    openai_api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text='OpenAI API key for GPT models'
    )

    # Skill-specific API keys (BRAVE_API_KEY, SERPER_API_KEY, etc.)
    skill_api_keys = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional API keys required by skills (e.g., BRAVE_API_KEY for web search)'
    )

    # Profile fields
    company_name = models.CharField(max_length=200, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def has_anthropic_key(self):
        """Check if user has set an Anthropic API key."""
        return bool(self.anthropic_api_key)

    @property
    def has_openai_key(self):
        """Check if user has set an OpenAI API key."""
        return bool(self.openai_api_key)
