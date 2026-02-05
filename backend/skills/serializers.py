"""
Skills serializers.
"""
from rest_framework import serializers
from .models import Skill, SkillRating


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill model."""
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Skill
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'short_description',
            'author',
            'author_url',
            'repository_url',
            'icon_url',
            'category',
            'category_display',
            'tags',
            'version',
            'install_count',
            'is_official',
            'is_featured',
            'average_rating',
            'required_tools',
            'required_env',
            'created_at',
            'updated_at',
        ]

    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if not ratings:
            return None
        return sum(r.rating for r in ratings) / len(ratings)


class SkillDetailSerializer(SkillSerializer):
    """Detailed serializer with SKILL.md content."""

    class Meta(SkillSerializer.Meta):
        fields = SkillSerializer.Meta.fields + ['skill_content']


class SkillRatingSerializer(serializers.ModelSerializer):
    """Serializer for skill ratings."""
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = SkillRating
        fields = [
            'id',
            'skill',
            'user_email',
            'rating',
            'review',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SkillInstallSerializer(serializers.Serializer):
    """Serializer for installing a skill to a workspace."""
    workspace_id = serializers.IntegerField()
    config = serializers.JSONField(required=False, default=dict)
