"""
URL routes for Google integration.
"""
from django.urls import path
from .views import (
    GmailOAuthInitView,
    GmailOAuthCallbackView,
    GmailConnectionView,
    GmailTestView,
)

urlpatterns = [
    path('oauth/init/', GmailOAuthInitView.as_view(), name='gmail-oauth-init'),
    path('oauth/callback/', GmailOAuthCallbackView.as_view(), name='gmail-oauth-callback'),
    path('connection/', GmailConnectionView.as_view(), name='gmail-connection'),
    path('test/', GmailTestView.as_view(), name='gmail-test'),
]
