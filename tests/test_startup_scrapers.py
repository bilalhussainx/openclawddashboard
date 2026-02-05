"""Test the startup scrapers."""
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import JobPreferences
from jobapply.startup_scrapers import scrape_hn_hiring, scrape_remoteok

# Enable startup boards for all users
for prefs in JobPreferences.objects.all():
    boards = prefs.enabled_boards or []
    if 'hn_hiring' not in boards:
        boards.append('hn_hiring')
    if 'remoteok' not in boards:
        boards.append('remoteok')
    prefs.enabled_boards = boards
    prefs.save()
    print(f"Enabled boards for {prefs.user.email}: {prefs.enabled_boards}")

# Test HN scraper
print("\n--- Testing HN Who's Hiring ---")
result = scrape_hn_hiring('python developer', max_results=5)
print(f"Success: {result['success']}, Total: {result['total']}")
if result['errors']:
    print(f"Errors: {result['errors']}")
for job in result['jobs'][:3]:
    print(f"  {job['title']} @ {job['company']} | {job['location']}")
    print(f"    URL: {job['job_url'][:80]}")
    print(f"    Desc: {job['description'][:100]}")
    print()

# Test RemoteOK scraper
print("\n--- Testing RemoteOK ---")
result = scrape_remoteok('python developer', max_results=5)
print(f"Success: {result['success']}, Total: {result['total']}")
if result['errors']:
    print(f"Errors: {result['errors']}")
for job in result['jobs'][:3]:
    print(f"  {job['title']} @ {job['company']} | {job['location']}")
    print(f"    URL: {job['job_url'][:80]}")
    print(f"    Desc: {job['description'][:100]}")
    print()

# Test with AI-focused search
print("\n--- Testing HN with 'AI engineer' ---")
result = scrape_hn_hiring('AI engineer', max_results=5)
print(f"Success: {result['success']}, Total: {result['total']}")
for job in result['jobs'][:3]:
    print(f"  {job['title']} @ {job['company']} | {job['location']}")

print("\n--- Testing RemoteOK with 'AI' ---")
result = scrape_remoteok('AI', max_results=5)
print(f"Success: {result['success']}, Total: {result['total']}")
for job in result['jobs'][:3]:
    print(f"  {job['title']} @ {job['company']} | {job['location']}")
