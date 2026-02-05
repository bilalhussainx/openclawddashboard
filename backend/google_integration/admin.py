"""
Admin configuration for Google integration.
"""
from django.contrib import admin
from .models import GmailConnection


@admin.register(GmailConnection)
class GmailConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_address', 'is_connected', 'updated_at']
    list_filter = ['is_connected']
    search_fields = ['user__email', 'email_address']
    readonly_fields = ['access_token', 'refresh_token', 'token_expiry', 'oauth_state']
