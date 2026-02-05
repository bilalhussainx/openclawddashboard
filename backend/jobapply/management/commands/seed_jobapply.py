"""
Seed Bilal's resume and default job preferences.
Usage: python manage.py seed_jobapply
"""
import os
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings


class Command(BaseCommand):
    help = 'Seed resume and job preferences for the first user'

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from jobapply.models import Resume, JobPreferences

        User = get_user_model()
        user = User.objects.first()
        if not user:
            self.stderr.write("No users found. Create a user first.")
            return

        self.stdout.write(f"Seeding job apply data for {user.email}...")

        # 1. Create resume record
        resume_path = os.path.join(settings.MEDIA_ROOT, 'resumes', 'Bilal-Hussain-Resume11.pdf')
        resume, created = Resume.objects.get_or_create(
            user=user,
            name='Bilal Hussain - Senior Developer',
            defaults={
                'file_type': 'pdf',
                'is_primary': True,
                'extracted_text': RESUME_TEXT,
                'parsed_data': RESUME_DATA,
            }
        )

        if created and os.path.exists(resume_path):
            with open(resume_path, 'rb') as f:
                resume.file.save('Bilal-Hussain-Resume11.pdf', File(f), save=True)
            self.stdout.write(self.style.SUCCESS(f"  Resume created: {resume.name}"))
        elif created:
            resume.save()
            self.stdout.write(self.style.WARNING(f"  Resume created (no PDF file found at {resume_path})"))
        else:
            self.stdout.write(f"  Resume already exists: {resume.name}")

        # 2. Create job preferences
        prefs, created = JobPreferences.objects.get_or_create(
            user=user,
            defaults={
                'keywords': [
                    'Django Developer',
                    'Python Developer',
                    'React Developer',
                    'Full Stack Developer',
                    'Backend Developer',
                    'Software Engineer',
                    'AI Engineer',
                ],
                'excluded_keywords': [
                    'C++', 'Java', '.NET', 'Director', 'VP',
                    'Principal Architect', 'Embedded', 'iOS', 'Android',
                ],
                'location': 'Toronto',
                'remote_ok': True,
                'enabled_boards': ['linkedin', 'indeed', 'glassdoor'],
                'auto_apply_enabled': True,
                'auto_apply_min_score': 70,
                'max_daily_applications': 15,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"  Job preferences created for {user.email}"))
        else:
            self.stdout.write(f"  Job preferences already exist for {user.email}")

        self.stdout.write(self.style.SUCCESS("Done!"))


# Pre-parsed resume text (from Bilal-Hussain-Resume11.pdf)
RESUME_TEXT = """Bilal Hussain
Toronto, Ontario (EST)
Senior Django + React Developer | Claude Code Power User

EDUCATION
Harvard College - BA Computer Science, May 2022

SKILLS
Python, Django, Django REST Framework, PostgreSQL, MongoDB, React, TypeScript,
Next.js, Docker, Playwright, AWS (EC2, S3, Lambda), Claude Code, Anthropic SDK,
REST APIs, GraphQL, Celery, Redis, Git, CI/CD

EXPERIENCE

Senior Full-Stack Developer | Penomo Protocol | Aug 2025 - Present
- Building DeFi platform with Django backend and React frontend
- Implementing real-time data pipelines with Celery and Redis
- Leading architecture decisions for microservices migration
- Using Claude Code for rapid prototyping and code generation

Lead Software Engineer | Healthynox | Aug 2019 - Dec 2021
- Led team of 5 developers building health-tech SaaS platform
- Designed and implemented RESTful API serving 50K+ daily requests
- Built real-time monitoring dashboard with React and WebSocket
- Reduced API response time by 40% through query optimization

Computer Science Instructor | Milton Academy | Aug 2022 - May 2024
- Taught AP Computer Science and Data Structures
- Developed curriculum covering Python, algorithms, and web development
- Mentored students in building full-stack projects

PROJECTS

EssayMentor AI - Multi-agent LLM system for essay feedback
- Built with Django, React, and Anthropic Claude API
- Implemented agent orchestration for structured writing feedback

CoreZenith - Real-time educational platform
- Django Channels for WebSocket-based live collaboration
- React frontend with TypeScript for type-safe components
"""

# Pre-parsed structured data
RESUME_DATA = {
    'name': 'Bilal Hussain',
    'email': '',
    'phone': '',
    'location': 'Toronto, Ontario',
    'summary': 'Senior Django + React Developer with 5+ years experience building full-stack applications. Harvard CS graduate with expertise in Python, Django, React, TypeScript, and AI/LLM integration.',
    'skills': [
        'Python', 'Django', 'Django REST Framework', 'PostgreSQL', 'MongoDB',
        'React', 'TypeScript', 'Next.js', 'Docker', 'Playwright',
        'AWS', 'Claude Code', 'Anthropic SDK', 'REST APIs', 'GraphQL',
        'Celery', 'Redis', 'Git', 'CI/CD', 'WebSocket',
    ],
    'experience': [
        {
            'title': 'Senior Full-Stack Developer',
            'company': 'Penomo Protocol',
            'dates': 'Aug 2025 - Present',
            'description': 'Building DeFi platform with Django backend and React frontend. Leading architecture decisions for microservices migration.',
        },
        {
            'title': 'Lead Software Engineer',
            'company': 'Healthynox',
            'dates': 'Aug 2019 - Dec 2021',
            'description': 'Led team of 5 developers building health-tech SaaS platform. Designed RESTful API serving 50K+ daily requests.',
        },
        {
            'title': 'Computer Science Instructor',
            'company': 'Milton Academy',
            'dates': 'Aug 2022 - May 2024',
            'description': 'Taught AP Computer Science and Data Structures. Developed curriculum covering Python, algorithms, and web development.',
        },
    ],
    'education': [
        {
            'degree': 'BA Computer Science',
            'school': 'Harvard College',
            'year': '2022',
        },
    ],
}
