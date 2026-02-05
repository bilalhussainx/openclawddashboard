"""Trigger startup search and re-score all listings."""
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import JobListing, JobPreferences, Resume
from jobapply.scoring import score_job_for_user
from jobapply.tasks import discover_jobs

user_id = 1

# 1. Re-score all existing listings with new algorithm
prefs = JobPreferences.objects.get(user_id=user_id)
resume = Resume.objects.filter(user_id=user_id, is_primary=True).first()
resume_data = resume.parsed_data if resume else {}

listings = JobListing.objects.filter(user_id=user_id)
print(f"Re-scoring {listings.count()} existing listings...")
updated = 0
for listing in listings:
    job_dict = {
        'title': listing.title,
        'description': listing.description,
        'location': listing.location,
    }
    scoring = score_job_for_user(job_dict, resume_data, prefs)
    if listing.match_score != scoring['score']:
        listing.match_score = scoring['score']
        listing.score_breakdown = scoring['breakdown']
        listing.matched_keywords = scoring['matched_keywords']
        listing.save(update_fields=['match_score', 'score_breakdown', 'matched_keywords'])
        updated += 1
print(f"Updated {updated} listings")

# 2. Run startup board search
print("\nRunning startup board search...")
result = discover_jobs(user_id, boards_override=['hn_hiring', 'remoteok'])
print(f"Startup search result: {result}")

# 3. Run full search (all boards)
print("\nRunning full search (all boards)...")
result = discover_jobs(user_id)
print(f"Full search result: {result}")

# 4. Show top results
total = JobListing.objects.filter(user_id=user_id).count()
above70 = JobListing.objects.filter(user_id=user_id, match_score__gte=70).count()
startup = JobListing.objects.filter(user_id=user_id, source_board__in=['hn_hiring', 'remoteok']).count()
print(f"\nTotal listings: {total}")
print(f"Score >= 70: {above70}")
print(f"From startup boards: {startup}")

print("\nTop 10 startup jobs:")
for l in JobListing.objects.filter(user_id=user_id, source_board__in=['hn_hiring', 'remoteok']).order_by('-match_score')[:10]:
    print(f"  Score: {l.match_score} | {l.title} @ {l.company} | {l.source_board}")
    print(f"    Matched: {l.matched_keywords}")

print("\nTop 10 overall:")
for l in JobListing.objects.filter(user_id=user_id).order_by('-match_score')[:10]:
    print(f"  Score: {l.match_score} | {l.title} @ {l.company} | {l.source_board}")
