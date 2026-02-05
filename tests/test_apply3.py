"""Test apply automation with various URLs."""
import os, django, time
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from playwright.sync_api import sync_playwright

resume_data = {
    'name': 'Bilal Hussain',
    'email': 'bilalhussain.v1@gmail.com',
    'phone': '4379071483',
    'location': 'Toronto, Ontario',
    'linkedin': 'https://linkedin.com/in/bilalhussain',
    'github': 'https://github.com/bilalhussainx',
}

# Let's navigate to a few career pages and see what we get
test_urls = [
    'https://khanacademy.org/careers',
    'https://www.singularity6.com/careers',
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    )
    page = context.new_page()

    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print(f"{'='*60}")
        try:
            response = page.goto(url, wait_until='load', timeout=15000)
            time.sleep(3)
            final_url = page.url
            print(f"  Status: {response.status if response else 'None'}")
            print(f"  Final URL: {final_url}")

            from jobapply.playwright_apply import detect_ats
            ats = detect_ats(final_url)
            print(f"  ATS: {ats}")

            # Check for ATS-specific patterns in page content
            body = page.inner_text('body')[:2000].lower()
            ats_hints = []
            if 'greenhouse' in body or 'greenhouse' in final_url:
                ats_hints.append('greenhouse')
            if 'lever' in body or 'lever' in final_url:
                ats_hints.append('lever')
            if 'workday' in body or 'workday' in final_url:
                ats_hints.append('workday')
            if 'ashby' in body or 'ashby' in final_url:
                ats_hints.append('ashby')
            print(f"  ATS hints in body: {ats_hints or 'none'}")

            # Check for iframe-embedded ATS
            iframes = page.locator('iframe').all()
            for iframe in iframes[:3]:
                src = iframe.get_attribute('src') or ''
                if src:
                    print(f"  iframe src: {src[:100]}")

            # Check for Apply links
            apply_links = page.locator('a:has-text("Apply"), a:has-text("apply"), button:has-text("Apply")').all()
            print(f"  Apply links: {len(apply_links)}")
            for al in apply_links[:5]:
                try:
                    href = al.get_attribute('href') or ''
                    text = al.inner_text()[:40]
                    print(f"    '{text}' -> {href[:100]}")
                except:
                    pass

        except Exception as e:
            print(f"  Error: {e}")

    browser.close()

# Now test with actual Greenhouse URL (Anthropic)
print(f"\n{'='*60}")
print("Testing real Greenhouse: boards.greenhouse.io/anthropic")
print(f"{'='*60}")

from jobapply.playwright_apply import apply_to_job_with_playwright

# Get first real job from Anthropic Greenhouse
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    )
    page = context.new_page()
    page.goto('https://boards.greenhouse.io/anthropic', wait_until='load', timeout=20000)
    time.sleep(3)
    print(f"  Page URL: {page.url}")

    # Find first job link
    job_links = page.locator('a[href*="/jobs/"]').all()
    print(f"  Job links: {len(job_links)}")
    job_url = None
    for jl in job_links[:5]:
        href = jl.get_attribute('href') or ''
        text = jl.inner_text()[:60]
        print(f"    '{text}' -> {href[:100]}")
        if not job_url and '/jobs/' in href:
            job_url = href if href.startswith('http') else f"https://boards.greenhouse.io{href}"
    browser.close()

if job_url:
    print(f"\nTesting apply to: {job_url}")
    result = apply_to_job_with_playwright(
        job_url=job_url,
        resume_data=resume_data,
        cover_letter='',
        resume_file_path='/app/media/resumes/bilal_hussain_resume.pdf',
    )
    print(f"\n  Success: {result.get('success')}")
    print(f"  Method: {result.get('method')}")
    print(f"  Error: {result.get('error')}")
    for step in result.get('log', []):
        print(f"  [{step['step']}] {step['action']}: {step['result'][:100]}")
else:
    print("No job URL found to test")
