"""
Management command to sync skills from ClawHub registry.

Usage:
    python manage.py sync_clawhub
    python manage.py sync_clawhub --limit 100
"""
from django.core.management.base import BaseCommand
from skills.clawhub_sync import sync_clawhub_skills, fetch_clawhub_skills, sync_skills_to_database


class Command(BaseCommand):
    help = 'Sync skills from ClawHub registry to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='Maximum number of skills to fetch'
        )
        parser.add_argument(
            '--defaults-only',
            action='store_true',
            help='Only sync default/curated skills without API call'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting ClawHub skill sync...')

        if options['defaults_only']:
            from skills.clawhub_sync import get_default_skills
            skills = get_default_skills()
            self.stdout.write(f'Using {len(skills)} default skills')
        else:
            skills = fetch_clawhub_skills(limit=options['limit'])
            self.stdout.write(f'Fetched {len(skills)} skills from ClawHub')

        stats = sync_skills_to_database(skills)

        self.stdout.write(self.style.SUCCESS(
            f'Sync complete: {stats["created"]} created, {stats["updated"]} updated, {stats["errors"]} errors'
        ))
