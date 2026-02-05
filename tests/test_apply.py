"""Test the career page apply automation."""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.playwright_apply import apply_to_job_with_playwright, detect_ats

# Test ATS detection (including redirect URLs)
print("=== ATS Detection Tests ===")
test_urls = [
    'https://grnh.se/b6ff87e61us',
    'https://boards.greenhouse.io/canonical/jobs/123',
    'https://jobs.lever.co/stripe/abc',
]
for u in test_urls:
    ats = detect_ats(u)
    print(f"  {ats:20s} <- {u[:60]}")

# Test with Greenhouse URL - Canonical (Ubuntu)
print("\n=== Live Test: Greenhouse URL (Canonical/Ubuntu) ===")
result = apply_to_job_with_playwright(
    job_url='https://grnh.se/b6ff87e61us',
    resume_data={
        'name': 'Bilal Hussain',
        'email': 'bilalhussain.v1@gmail.com',
        'phone': '4379071483',
        'location': 'Toronto, Ontario',
        'linkedin': 'https://linkedin.com/in/bilalhussain',
        'github': 'https://github.com/bilalhussainx',
    },
    cover_letter='',
    resume_file_path='/app/media/resumes/bilal_hussain_resume.pdf',
)
print(f"\nResult:")
print(f"  Success: {result.get('success')}")
print(f"  Method: {result.get('method')}")
print(f"  Error: {result.get('error')}")
print(f"\nSteps ({len(result.get('log', []))}):")
for step in result.get('log', []):
    print(f"  [{step['step']}] {step['action']}: {step['result'][:100]}")
