"""
Skills views - Marketplace API endpoints.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Avg

from .models import Skill, SkillRating
from .serializers import (
    SkillSerializer,
    SkillDetailSerializer,
    SkillRatingSerializer,
    SkillInstallSerializer,
)
from workspaces.models import Workspace, InstalledSkill


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for browsing the skills marketplace.

    list: GET /api/skills/
    retrieve: GET /api/skills/{slug}/
    """
    queryset = Skill.objects.filter(is_active=True)
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'tags', 'author']
    ordering_fields = ['install_count', 'created_at', 'name']
    ordering = ['-is_featured', '-install_count']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'featured', 'categories']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SkillDetailSerializer
        return SkillSerializer

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Get featured skills.

        GET /api/skills/featured/
        """
        featured = self.queryset.filter(is_featured=True)[:10]
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get skill categories with counts.

        GET /api/skills/categories/
        """
        categories = []
        for choice in Skill.Category.choices:
            count = self.queryset.filter(category=choice[0]).count()
            categories.append({
                'value': choice[0],
                'label': choice[1],
                'count': count,
            })
        return Response(categories)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Get skills by category.

        GET /api/skills/by-category/?category=productivity
        """
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'error': 'category parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        skills = self.queryset.filter(category=category)
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def install(self, request, slug=None):
        """
        Install a skill to a workspace.

        POST /api/skills/{slug}/install/

        Checks for required API keys and triggers installation task.
        """
        skill = self.get_object()
        serializer = SkillInstallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workspace_id = serializer.validated_data['workspace_id']
        config = serializer.validated_data.get('config', {})

        # Verify workspace ownership
        workspace = get_object_or_404(
            Workspace,
            id=workspace_id,
            owner=request.user
        )

        # Check if already installed
        if InstalledSkill.objects.filter(workspace=workspace, skill=skill).exists():
            return Response(
                {'error': 'Skill already installed in this workspace'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for missing required API keys
        missing_env = []
        user_skill_keys = getattr(request.user, 'skill_api_keys', None) or {}
        required_env = skill.required_env or []

        for env_var in required_env:
            # Check in skill_api_keys first, then standard user fields
            if env_var not in user_skill_keys:
                # Also check standard API key fields
                if env_var == 'ANTHROPIC_API_KEY' and request.user.anthropic_api_key:
                    continue
                if env_var == 'OPENAI_API_KEY' and request.user.openai_api_key:
                    continue
                missing_env.append(env_var)

        # Determine initial install status
        install_status = (
            InstalledSkill.InstallStatus.MISSING_REQUIREMENTS
            if missing_env
            else InstalledSkill.InstallStatus.PENDING
        )

        # Install the skill
        installed = InstalledSkill.objects.create(
            workspace=workspace,
            skill=skill,
            config=config,
            install_status=install_status
        )

        # Update install count
        skill.install_count += 1
        skill.save()

        # Trigger installation task if no missing requirements
        if not missing_env:
            from workspaces.tasks import install_skill_in_container
            install_skill_in_container.delay(workspace.id, installed.id)

        return Response({
            'message': f'{skill.name} installed successfully',
            'installed_skill_id': installed.id,
            'install_status': install_status,
            'missing_requirements': missing_env,
        })

    @action(detail=True, methods=['get', 'post'])
    def ratings(self, request, slug=None):
        """
        Get or create ratings for a skill.

        GET /api/skills/{slug}/ratings/
        POST /api/skills/{slug}/ratings/
        """
        skill = self.get_object()

        if request.method == 'GET':
            ratings = skill.ratings.all()
            serializer = SkillRatingSerializer(ratings, many=True)
            return Response({
                'ratings': serializer.data,
                'average': ratings.aggregate(avg=Avg('rating'))['avg'],
                'count': ratings.count(),
            })

        # POST - create rating
        serializer = SkillRatingSerializer(data={
            **request.data,
            'skill': skill.id,
        })
        serializer.is_valid(raise_exception=True)

        # Check for existing rating
        existing = SkillRating.objects.filter(
            skill=skill,
            user=request.user
        ).first()

        if existing:
            existing.rating = serializer.validated_data['rating']
            existing.review = serializer.validated_data.get('review', '')
            existing.save()
            return Response(SkillRatingSerializer(existing).data)

        rating = SkillRating.objects.create(
            skill=skill,
            user=request.user,
            **serializer.validated_data
        )
        return Response(
            SkillRatingSerializer(rating).data,
            status=status.HTTP_201_CREATED
        )
