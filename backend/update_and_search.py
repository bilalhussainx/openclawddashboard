"""Update keywords, adjust scoring preferences, and trigger searches."""
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import JobPreferences

# Update keywords for all users
new_keywords = [
    'Junior Software Developer',
    'Junior Developer',
    'Web Developer',
    'Django Developer',
    'Python Developer',
    'React Developer',
    'Full Stack Developer',
    'Backend Developer',
    'Software Engineer',
    'AI Engineer',
    'AI Developer',
    'Claude Developer',
]

for prefs in JobPreferences.objects.all():
    prefs.keywords = new_keywords
    prefs.save()
    print(f"Updated keywords for {prefs.user.email}: {prefs.keywords}")

print("\nKeywords updated. Ready to trigger searches.")
