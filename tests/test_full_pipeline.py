"""Test full pipeline: Ollama cover letter + Greenhouse apply."""
import os, django, time
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import JobListing, JobApplication, Resume
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
resume = Resume.objects.filter(user=user, is_primary=True).first()

print(f"User: {user.email}")
print(f"Resume: {resume.parsed_data.get('name', 'N/A')} | email={resume.parsed_data.get('email', 'N/A')}")
print(f"Resume file: {resume.file.path if resume.file else 'NONE'}")

# Get test listing
from hashlib import sha256
test_url = 'https://job-boards.greenhouse.io/anthropic/jobs/5106251008'
url_hash = sha256(test_url.encode()).hexdigest()
listing = JobListing.objects.filter(url_hash=url_hash).first()
if not listing:
    print("Test listing not found, creating...")
    listing = JobListing.objects.create(
        user=user, url_hash=url_hash,
        title='External Affairs, US Federal (Test)',
        company='Anthropic', location='Washington, DC',
        url=test_url, description='Policy role at Anthropic working on AI safety and government relations.',
        source_board='greenhouse_test', match_score=80,
    )

# Clean up previous test applications
JobApplication.objects.filter(user=user, listing=listing).delete()

# Create application
app = JobApplication.objects.create(
    user=user, listing=listing, resume=resume, status='queued',
)
print(f"\nApplication ID={app.id}")

# Run pipeline
print("\n--- Running process_application ---")
start = time.time()
from jobapply.tasks import process_application
result = process_application(app.id)
elapsed = time.time() - start
print(f"Completed in {elapsed:.1f}s")
print(f"Result: {result}")

# Check final state
app.refresh_from_db()
print(f"\n--- Final State ---")
print(f"Status: {app.status}")
print(f"Applied via: {app.applied_via}")
print(f"Error: {app.error_message[:200] if app.error_message else 'None'}")
print(f"Cover letter ({len(app.cover_letter)} chars):")
if app.cover_letter:
    print(app.cover_letter[:500])
print(f"\nAutomation log ({len(app.automation_log)} steps):")
for step in app.automation_log:
    print(f"  [{step.get('step')}] {step.get('action')}: {step.get('result', '')[:80]}")
