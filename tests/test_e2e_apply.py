"""End-to-end test: simulate Apply button click through the full pipeline."""
import os, django, time
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import JobListing, JobApplication, Resume
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
resume = Resume.objects.filter(user=user, is_primary=True).first()

print(f"User: {user.email}")
print(f"Resume: {resume.name if resume else 'None'} (file: {resume.file if resume else 'N/A'})")
print(f"Resume data: name={resume.parsed_data.get('name')}, email={resume.parsed_data.get('email')}")

# Create a test listing with a known working Greenhouse URL
from hashlib import sha256
test_url = 'https://job-boards.greenhouse.io/anthropic/jobs/5106251008'
url_hash = sha256(test_url.encode()).hexdigest()

listing, created = JobListing.objects.get_or_create(
    user=user,
    url_hash=url_hash,
    defaults={
        'title': 'External Affairs, US Federal (Test)',
        'company': 'Anthropic',
        'location': 'Washington, DC',
        'url': test_url,
        'description': 'Test job for apply automation',
        'source_board': 'greenhouse_test',
        'match_score': 80,
    }
)
print(f"\nTest listing: {listing.title} (ID={listing.id}, created={created})")
print(f"URL: {listing.url}")

# Delete any existing application for this listing
JobApplication.objects.filter(user=user, listing=listing).delete()

# Simulate Apply button: create application and trigger task
app = JobApplication.objects.create(
    user=user,
    listing=listing,
    resume=resume,
    status='queued',
)
print(f"\nApplication created: ID={app.id}, status={app.status}")

# Run process_application directly (not via Celery delay - for testing)
from jobapply.tasks import process_application
print("\nRunning process_application (synchronous)...")
result = process_application(app.id)
print(f"\nResult: {result}")

# Refresh from DB
app.refresh_from_db()
print(f"\nApplication status: {app.status}")
print(f"Applied via: {app.applied_via}")
print(f"Error: {app.error_message[:200] if app.error_message else 'None'}")
print(f"Automation log steps: {len(app.automation_log)}")
for step in app.automation_log:
    print(f"  [{step.get('step')}] {step.get('action')}: {step.get('result', '')[:80]}")
