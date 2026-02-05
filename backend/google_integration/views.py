"""
Gmail OAuth views for connecting user's Gmail account.
"""
import logging
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GmailConnection
from .serializers import GmailConnectionSerializer

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

# Scopes needed for Gmail read access
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
]


class GmailOAuthInitView(APIView):
    """
    GET /api/google/oauth/init/
    Returns the Google OAuth URL for the user to authorize Gmail access.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return Response(
                {'error': 'Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Generate state token for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in user's Gmail connection (create if needed)
        gmail_conn, _ = GmailConnection.objects.get_or_create(user=request.user)
        gmail_conn.oauth_state = state
        gmail_conn.save()

        # Build OAuth URL
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': ' '.join(GMAIL_SCOPES),
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent',  # Always show consent screen (ensures refresh token)
            'state': state,
        }

        oauth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

        return Response({
            'oauth_url': oauth_url,
            'state': state,
        })


class GmailOAuthCallbackView(APIView):
    """
    GET /api/google/oauth/callback/
    Handles the OAuth callback from Google, exchanges code for tokens.
    """
    permission_classes = [AllowAny]  # Callback doesn't have JWT

    def get(self, request):
        import requests as http_requests

        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')

        # Frontend URL to redirect to after OAuth
        frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else 'http://localhost:3000'

        if error:
            logger.error(f"Google OAuth error: {error}")
            return redirect(f"{frontend_url}/dashboard/jobapply/integrations?error={error}")

        if not code or not state:
            return redirect(f"{frontend_url}/dashboard/jobapply/integrations?error=missing_params")

        # Find user by state token
        try:
            gmail_conn = GmailConnection.objects.get(oauth_state=state)
        except GmailConnection.DoesNotExist:
            logger.error(f"Invalid OAuth state: {state}")
            return redirect(f"{frontend_url}/dashboard/jobapply/integrations?error=invalid_state")

        # Exchange code for tokens
        try:
            token_response = http_requests.post(GOOGLE_TOKEN_URL, data={
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            })

            if not token_response.ok:
                logger.error(f"Token exchange failed: {token_response.text}")
                return redirect(f"{frontend_url}/dashboard/jobapply/integrations?error=token_exchange_failed")

            tokens = token_response.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')
            expires_in = tokens.get('expires_in', 3600)

            if not access_token:
                return redirect(f"{frontend_url}/dashboard/jobapply/integrations?error=no_access_token")

        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return redirect(f"{frontend_url}/dashboard/jobapply/integrations?error=token_exchange_error")

        # Get user's email address
        try:
            userinfo_response = http_requests.get(
                GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if userinfo_response.ok:
                userinfo = userinfo_response.json()
                email_address = userinfo.get('email', '')
            else:
                email_address = ''
        except Exception as e:
            logger.warning(f"Failed to get user email: {e}")
            email_address = ''

        # Save tokens
        gmail_conn.access_token = access_token
        gmail_conn.refresh_token = refresh_token or gmail_conn.refresh_token  # Keep old if not provided
        gmail_conn.token_expiry = timezone.now() + timezone.timedelta(seconds=expires_in)
        gmail_conn.email_address = email_address
        gmail_conn.is_connected = True
        gmail_conn.oauth_state = ''  # Clear state after use
        gmail_conn.save()

        logger.info(f"Gmail connected for user {gmail_conn.user.id}: {email_address}")

        return redirect(f"{frontend_url}/dashboard/jobapply/integrations?success=true")


class GmailConnectionView(APIView):
    """
    GET /api/google/connection/ - Check Gmail connection status
    DELETE /api/google/connection/ - Disconnect Gmail
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            gmail_conn = request.user.gmail_connection
            return Response(GmailConnectionSerializer(gmail_conn).data)
        except GmailConnection.DoesNotExist:
            return Response({
                'email_address': '',
                'is_connected': False,
                'created_at': None,
                'updated_at': None,
            })

    def delete(self, request):
        try:
            gmail_conn = request.user.gmail_connection
            gmail_conn.access_token = ''
            gmail_conn.refresh_token = ''
            gmail_conn.token_expiry = None
            gmail_conn.is_connected = False
            gmail_conn.save()
            logger.info(f"Gmail disconnected for user {request.user.id}")
            return Response({'status': 'disconnected'})
        except GmailConnection.DoesNotExist:
            return Response({'status': 'not_connected'})


class GmailTestView(APIView):
    """
    GET /api/google/test/
    Test Gmail connection by fetching recent emails.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .gmail_service import search_emails

        emails = search_emails(request.user, 'newer_than:1d', max_results=5)

        if emails:
            return Response({
                'status': 'connected',
                'recent_emails': len(emails),
                'sample': [{'subject': e['subject'], 'from': e['from']} for e in emails[:3]]
            })
        else:
            return Response({
                'status': 'no_emails_or_not_connected',
                'recent_emails': 0,
                'sample': []
            })
