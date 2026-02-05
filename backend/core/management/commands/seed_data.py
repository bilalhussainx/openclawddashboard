"""
Management command to seed initial data for development.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed initial data for development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Create billing plans
        self._create_billing_plans()

        # Create sample skills
        self._create_sample_skills()

        # Create test user if not exists
        self._create_test_user()

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    def _create_billing_plans(self):
        from billing.models import BillingPlan

        plans = [
            {
                'name': 'Free',
                'plan_type': 'free',
                'description': 'Get started with basic features',
                'price_monthly': Decimal('0.00'),
                'price_yearly': Decimal('0.00'),
                'max_workspaces': 1,
                'max_channels': 1,
                'max_messages_per_month': 1000,
                'max_skills': 5,
                'allowed_models': ['claude-3-5-haiku-20241022'],
                'features': [
                    '1 workspace',
                    '1 channel (Telegram or Discord)',
                    '1,000 messages/month',
                    'Claude Haiku model',
                    'Community support',
                ],
                'is_default': True,
            },
            {
                'name': 'Pro',
                'plan_type': 'pro',
                'description': 'For power users and small teams',
                'price_monthly': Decimal('49.00'),
                'price_yearly': Decimal('470.00'),
                'max_workspaces': 3,
                'max_channels': 3,
                'max_messages_per_month': 10000,
                'max_skills': 20,
                'allowed_models': [
                    'claude-opus-4-20250514',
                    'claude-sonnet-4-20250514',
                    'claude-3-5-haiku-20241022',
                    'gpt-4-turbo-preview',
                    'gpt-3.5-turbo',
                ],
                'features': [
                    '3 workspaces',
                    '3 channels',
                    '10,000 messages/month',
                    'All AI models',
                    '20 custom skills',
                    'Email support',
                ],
            },
            {
                'name': 'Enterprise',
                'plan_type': 'enterprise',
                'description': 'For large teams and organizations',
                'price_monthly': Decimal('199.00'),
                'price_yearly': Decimal('1990.00'),
                'max_workspaces': 100,
                'max_channels': 100,
                'max_messages_per_month': 100000,
                'max_skills': 1000,
                'allowed_models': [
                    'claude-opus-4-20250514',
                    'claude-sonnet-4-20250514',
                    'claude-3-5-haiku-20241022',
                    'gpt-4-turbo-preview',
                    'gpt-3.5-turbo',
                ],
                'features': [
                    'Unlimited workspaces',
                    'Unlimited channels',
                    '100,000 messages/month',
                    'All AI models',
                    'Unlimited skills',
                    'White-label option',
                    'Priority support',
                    'Custom integrations',
                ],
            },
        ]

        for plan_data in plans:
            plan, created = BillingPlan.objects.update_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status} plan: {plan.name}')

    def _create_sample_skills(self):
        from skills.models import Skill

        skills = [
            {
                'name': 'Web Search',
                'slug': 'web-search',
                'description': 'Search the web for information using various search engines.',
                'short_description': 'Search the web for real-time information',
                'author': 'OpenClaw',
                'repository_url': 'https://github.com/openclaw/skills-web-search',
                'category': 'productivity',
                'tags': ['search', 'web', 'research'],
                'is_official': True,
                'is_featured': True,
            },
            {
                'name': 'Code Executor',
                'slug': 'code-executor',
                'description': 'Execute code in various programming languages safely.',
                'short_description': 'Run code in Python, JavaScript, and more',
                'author': 'OpenClaw',
                'repository_url': 'https://github.com/openclaw/skills-code-executor',
                'category': 'development',
                'tags': ['code', 'python', 'javascript', 'execution'],
                'is_official': True,
                'is_featured': True,
            },
            {
                'name': 'File Manager',
                'slug': 'file-manager',
                'description': 'Read, write, and manage files in the workspace.',
                'short_description': 'Manage files and documents',
                'author': 'OpenClaw',
                'repository_url': 'https://github.com/openclaw/skills-file-manager',
                'category': 'productivity',
                'tags': ['files', 'documents', 'storage'],
                'is_official': True,
            },
            {
                'name': 'Calendar Integration',
                'slug': 'calendar',
                'description': 'Connect to Google Calendar or other calendar services.',
                'short_description': 'Manage your calendar and events',
                'author': 'Community',
                'repository_url': 'https://github.com/openclaw-community/skills-calendar',
                'category': 'productivity',
                'tags': ['calendar', 'events', 'scheduling'],
            },
            {
                'name': 'Weather',
                'slug': 'weather',
                'description': 'Get current weather and forecasts for any location.',
                'short_description': 'Check weather conditions worldwide',
                'author': 'Community',
                'repository_url': 'https://github.com/openclaw-community/skills-weather',
                'category': 'fun',
                'tags': ['weather', 'forecast', 'location'],
            },
        ]

        for skill_data in skills:
            skill, created = Skill.objects.update_or_create(
                slug=skill_data['slug'],
                defaults=skill_data
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status} skill: {skill.name}')

    def _create_test_user(self):
        email = 'test@example.com'
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                email=email,
                password='testpass123',
                first_name='Test',
                last_name='User',
            )
            self.stdout.write(f'  Created test user: {email} (password: testpass123)')
        else:
            self.stdout.write(f'  Test user already exists: {email}')
