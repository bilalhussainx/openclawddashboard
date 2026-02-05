"""Run targeted AI job search and save results."""
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.tasks import discover_jobs

# Run job discovery for user 1 (test@example.com) with updated AI keywords
result = discover_jobs(1)
print(f"Discovery result: {result}")

# Show top scores after discovery
from jobapply.models import JobListing
top = JobListing.objects.filter(user_id=1).order_by('-match_score')[:10]
print("\nTop 10 after re-discovery:")
for l in top:
    print(f"  Score: {l.match_score} | {l.title} @ {l.company}")
    print(f"    Matched: {l.matched_keywords}")

total = JobListing.objects.filter(user_id=1).count()
above70 = JobListing.objects.filter(user_id=1, match_score__gte=70).count()
above50 = JobListing.objects.filter(user_id=1, match_score__gte=50).count()
print(f"\nTotal listings: {total}")
print(f"Score >= 70 (auto-apply): {above70}")
print(f"Score >= 50: {above50}")
