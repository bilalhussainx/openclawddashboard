"""
Skills admin configuration.
"""
from django.contrib import admin
from .models import Skill, SkillRating


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'slug',
        'author',
        'category',
        'install_count',
        'is_official',
        'is_featured',
        'is_active',
    ]
    list_filter = ['category', 'is_official', 'is_featured', 'is_active']
    search_fields = ['name', 'slug', 'author', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['install_count', 'created_at', 'updated_at']


@admin.register(SkillRating)
class SkillRatingAdmin(admin.ModelAdmin):
    list_display = ['skill', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['skill__name', 'user__email']
