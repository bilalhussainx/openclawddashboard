"""Final test: Ollama cover letter + resume upload + Greenhouse apply."""
import os, django, time
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import JobListing, JobApplication, Resume
from django.contrib.auth import get_user_model
from hashlib import sha256

User = get_user_model()
# Use user 1 (test@example.com) who has the job listings
user = User.objects.get(id=1)
resume = Resume.objects.filter(user=user, is_primary=True).first()

print(f"User: {user.email} (ID={user.id})")
print(f"Resume: name={resume.parsed_data.get('name')} email={resume.parsed_data.get('email')} phone={resume.parsed_data.get('phone')}")
print(f"Resume file: {resume.file.name}")
print(f"File exists: {os.path.exists(resume.file.path)}")

# Use test listing
test_url = 'https://job-boards.greenhouse.io/anthropic/jobs/5106251008'
url_hash = sha256(test_url.encode()).hexdigest()
listing = JobListing.objects.filter(user=user, url_hash=url_hash).first()
if not listing:
    listing = JobListing.objects.create(
        user=user, url_hash=url_hash,
        title='External Affairs, US Federal (Test)',
        company='Anthropic', location='Washington, DC',
        url=test_url,
        description='Policy role at Anthropic working on AI safety and government relations. Requires strong communication skills and understanding of AI policy.',
        source_board='greenhouse_test', match_score=80,
    )

# Clean up and create fresh application
JobApplication.objects.filter(user=user, listing=listing).delete()
app = JobApplication.objects.create(
    user=user, listing=listing, resume=resume, status='queued',
)
print(f"\nApp ID={app.id} | Listing: {listing.title}")

# Run
print("\n--- Running pipeline ---")
start = time.time()
from jobapply.tasks import process_application
result = process_application(app.id)
elapsed = time.time() - start
print(f"Done in {elapsed:.1f}s | Result: {result}")

# Final state
app.refresh_from_db()
print(f"\n=== RESULT ===")
print(f"Status: {app.status}")
print(f"Applied via: {app.applied_via}")
if app.error_message:
    print(f"Error: {app.error_message[:200]}")

if app.cover_letter:
    print(f"\nCover letter ({len(app.cover_letter)} chars):")
    print(app.cover_letter[:400])
    print("...")

print(f"\nAutomation log:")
for step in app.automation_log:
    print(f"  [{step.get('step')}] {step.get('action')}: {step.get('result', '')[:80]}")
