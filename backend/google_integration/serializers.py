"""
Serializers for Gmail connection.
"""
from rest_framework import serializers
from .models import GmailConnection


class GmailConnectionSerializer(serializers.ModelSerializer):
    """Serializer for Gmail connection status."""

    class Meta:
        model = GmailConnection
        fields = ['email_address', 'is_connected', 'created_at', 'updated_at']
        read_only_fields = fields
