"""
Gmail API service for fetching Greenhouse verification codes.
"""
import base64
import logging
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_gmail_service(user):
    """
    Get authenticated Gmail API service for a user.
    Returns None if user doesn't have Gmail connected or tokens are invalid.
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request

    try:
        gmail_conn = user.gmail_connection
        if not gmail_conn.is_connected or not gmail_conn.refresh_token:
            logger.warning(f"Gmail not connected for user {user.id}")
            return None
    except Exception:
        logger.warning(f"No Gmail connection for user {user.id}")
        return None

    try:
        # Build credentials from stored tokens
        credentials = Credentials(
            token=gmail_conn.access_token,
            refresh_token=gmail_conn.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )

        # Refresh if expired
        if credentials.expired or not credentials.valid:
            logger.info(f"Refreshing Gmail token for user {user.id}")
            credentials.refresh(Request())

            # Update stored tokens
            gmail_conn.access_token = credentials.token
            gmail_conn.token_expiry = datetime.fromtimestamp(
                credentials.expiry.timestamp(), tz=timezone.utc
            ) if credentials.expiry else None
            gmail_conn.save()

        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        return service

    except Exception as e:
        logger.error(f"Failed to get Gmail service for user {user.id}: {e}")
        # Mark as disconnected if refresh failed
        try:
            gmail_conn.is_connected = False
            gmail_conn.save()
        except Exception:
            pass
        return None


def fetch_greenhouse_verification_code(user_or_id, max_age_minutes=5):
    """
    Search Gmail for recent Greenhouse verification code emails.
    Returns the code as string, or None if not found.

    Args:
        user_or_id: User instance or user ID
        max_age_minutes: Only look at emails from the last N minutes
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if isinstance(user_or_id, int):
        try:
            user = User.objects.get(id=user_or_id)
        except User.DoesNotExist:
            logger.error(f"User {user_or_id} not found")
            return None
    else:
        user = user_or_id

    service = get_gmail_service(user)
    if not service:
        return None

    try:
        # Calculate time filter
        after_timestamp = int((timezone.now() - timedelta(minutes=max_age_minutes)).timestamp())

        # Search for Greenhouse verification emails
        # Common senders: noreply@greenhouse.io, verify@greenhouse.io
        query = f'from:(greenhouse.io) subject:(security code OR verification) after:{after_timestamp}'

        logger.info(f"Searching Gmail with query: {query}")

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=5
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            logger.info(f"No Greenhouse verification emails found for user {user.id}")
            return None

        # Check each message for verification code
        for msg_meta in messages:
            msg = service.users().messages().get(
                userId='me',
                id=msg_meta['id'],
                format='full'
            ).execute()

            # Extract body
            body_text = _extract_email_body(msg)
            if not body_text:
                continue

            # Look for verification code patterns
            code = _extract_verification_code(body_text)
            if code:
                logger.info(f"Found Greenhouse verification code for user {user.id}: {code[:2]}****")
                return code

        logger.info(f"No verification code found in recent Greenhouse emails for user {user.id}")
        return None

    except Exception as e:
        logger.error(f"Error fetching Greenhouse verification code: {e}")
        return None


def _extract_email_body(message):
    """Extract plain text body from Gmail message."""
    try:
        payload = message.get('payload', {})

        # Check for plain text part
        if payload.get('mimeType') == 'text/plain':
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')

        # Check multipart
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')

            # Nested parts
            nested_parts = part.get('parts', [])
            for nested in nested_parts:
                if nested.get('mimeType') == 'text/plain':
                    data = nested.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')

        # Fallback: try to decode main body
        body_data = payload.get('body', {}).get('data', '')
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode('utf-8')

        return None

    except Exception as e:
        logger.error(f"Error extracting email body: {e}")
        return None


def _extract_verification_code(body_text):
    """
    Extract verification code from email body.
    Greenhouse codes are typically 6-8 alphanumeric characters.
    """
    if not body_text:
        return None

    # Common patterns for Greenhouse security codes
    patterns = [
        # "security code: ABC123" or "security code field: ABC123"
        r'security\s*code[:\s]+([A-Za-z0-9]{6,10})',
        # "verification code: ABC123"
        r'verification\s*code[:\s]+([A-Za-z0-9]{6,10})',
        # "code: ABC123" (generic)
        r'code[:\s]+([A-Za-z0-9]{6,10})',
        # "Copy and paste this code: ABC123"
        r'paste\s+this\s+code[:\s]+([A-Za-z0-9]{6,10})',
        # Standalone code after "is:" or "code:"
        r'(?:is|code)[:\s]+([A-Za-z0-9]{6,10})',
        # 8-character alphanumeric on its own line (common Greenhouse format like "hBVad3px")
        r'\n\s*([A-Za-z0-9]{8})\s*\n',
    ]

    for pattern in patterns:
        match = re.search(pattern, body_text, re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            # Validate: should be alphanumeric, 6-10 chars
            if code and 6 <= len(code) <= 10 and code.isalnum():
                return code

    return None


def search_emails(user, query, max_results=10):
    """
    Generic email search for a user.
    Returns list of {'id', 'subject', 'from', 'date', 'snippet'} dicts.
    """
    service = get_gmail_service(user)
    if not service:
        return []

    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        output = []

        for msg_meta in messages:
            msg = service.users().messages().get(
                userId='me',
                id=msg_meta['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
            output.append({
                'id': msg['id'],
                'subject': headers.get('Subject', ''),
                'from': headers.get('From', ''),
                'date': headers.get('Date', ''),
                'snippet': msg.get('snippet', ''),
            })

        return output

    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        return []
