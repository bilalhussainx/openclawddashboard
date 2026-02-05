"""
Core views - Authentication and user management endpoints.
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model

from .serializers import (
    UserSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    UpdateAPIKeysSerializer,
    ChangePasswordSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.

    POST /api/auth/register/
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Get tokens for the new user
        token_serializer = CustomTokenObtainPairSerializer()
        token = token_serializer.get_token(user)

        return Response({
            'user': UserSerializer(user).data,
            'access': str(token.access_token),
            'refresh': str(token),
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint - obtain JWT token pair.

    POST /api/auth/login/
    """
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token.

    POST /api/auth/refresh/
    """
    pass


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current authenticated user profile.

    GET /api/auth/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update current user profile.

    PUT/PATCH /api/auth/profile/
    """
    serializer = UserSerializer(
        request.user,
        data=request.data,
        partial=request.method == 'PATCH'
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_api_keys(request):
    """
    Update user API keys (Anthropic, OpenAI).

    PUT /api/auth/api-keys/
    """
    serializer = UpdateAPIKeysSerializer(
        request.user,
        data=request.data
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response({
        'message': 'API keys updated successfully',
        'has_anthropic_key': request.user.has_anthropic_key,
        'has_openai_key': request.user.has_openai_key,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password.

    POST /api/auth/change-password/
    """
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)

    request.user.set_password(serializer.validated_data['new_password'])
    request.user.save()

    return Response({'message': 'Password changed successfully'})


# Common skill API keys with descriptions
SKILL_API_KEY_INFO = {
    'BRAVE_API_KEY': {
        'name': 'Brave Search API Key',
        'description': 'Required for web search capabilities',
        'url': 'https://brave.com/search/api/',
    },
    'SERPER_API_KEY': {
        'name': 'Serper API Key',
        'description': 'Alternative search API for Google results',
        'url': 'https://serper.dev/',
    },
    'GITHUB_TOKEN': {
        'name': 'GitHub Personal Access Token',
        'description': 'Required for GitHub integration skills',
        'url': 'https://github.com/settings/tokens',
    },
    'TAVILY_API_KEY': {
        'name': 'Tavily API Key',
        'description': 'AI-powered search API',
        'url': 'https://tavily.com/',
    },
    'FIRECRAWL_API_KEY': {
        'name': 'Firecrawl API Key',
        'description': 'Web scraping and crawling',
        'url': 'https://firecrawl.dev/',
    },
    'BROWSERBASE_API_KEY': {
        'name': 'Browserbase API Key',
        'description': 'Browser automation service',
        'url': 'https://browserbase.com/',
    },
}


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def skill_api_keys(request):
    """
    Get or update skill-specific API keys.

    GET /api/auth/skill-api-keys/
    PUT /api/auth/skill-api-keys/
    """
    if request.method == 'GET':
        user_keys = request.user.skill_api_keys or {}

        # Build response with key info and configured status
        keys_info = []
        for key_name, info in SKILL_API_KEY_INFO.items():
            keys_info.append({
                'key': key_name,
                'name': info['name'],
                'description': info['description'],
                'url': info['url'],
                'is_configured': bool(user_keys.get(key_name)),
            })

        return Response({
            'keys': keys_info,
            'configured_count': sum(1 for k in keys_info if k['is_configured']),
        })

    # PUT - update skill API keys
    new_keys = request.data.get('keys', {})

    if not isinstance(new_keys, dict):
        return Response(
            {'error': 'keys must be a dictionary'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Merge with existing keys
    current_keys = request.user.skill_api_keys or {}

    for key_name, value in new_keys.items():
        if value is None or value == '':
            # Remove the key if empty
            current_keys.pop(key_name, None)
        else:
            current_keys[key_name] = value

    request.user.skill_api_keys = current_keys
    request.user.save()

    return Response({
        'message': 'Skill API keys updated successfully',
        'configured_keys': list(current_keys.keys()),
    })
