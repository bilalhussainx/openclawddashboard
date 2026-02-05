"""Temporary script to re-score all listings with updated algorithm."""
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import JobListing, JobPreferences, Resume
from jobapply.scoring import score_job_for_user

prefs = JobPreferences.objects.get(user_id=1)
resume = Resume.objects.filter(user_id=1, is_primary=True).first()
resume_data = resume.parsed_data if resume else {}

listings = JobListing.objects.filter(user_id=1)
print(f"Re-scoring {listings.count()} listings...")

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

top = JobListing.objects.filter(user_id=1).order_by('-match_score')[:15]
for l in top:
    print(f"Score: {l.match_score} | {l.title} @ {l.company}")
    print(f"  Matched: {l.matched_keywords}")
    if l.score_breakdown:
        print(f"  Breakdown: {l.score_breakdown}")
