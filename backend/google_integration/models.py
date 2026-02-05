"""
Gmail connection model for storing OAuth tokens.
"""
from django.conf import settings
from django.db import models


class GmailConnection(models.Model):
    """
    Stores Gmail OAuth tokens for a user.
    Used to fetch Greenhouse verification codes automatically.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gmail_connection'
    )

    # OAuth tokens (stored encrypted in production)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)

    # User's Gmail address
    email_address = models.EmailField(blank=True)

    # Connection status
    is_connected = models.BooleanField(default=False)

    # OAuth state for CSRF protection
    oauth_state = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gmail Connection'
        verbose_name_plural = 'Gmail Connections'

    def __str__(self):
        if self.is_connected:
            return f"{self.email_address} (connected)"
        return f"Gmail for {self.user.email} (disconnected)"
