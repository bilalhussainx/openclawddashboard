"""Debug: check what grnh.se page looks like."""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from playwright.sync_api import sync_playwright
import time

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

    print("Navigating to grnh.se...")
    response = page.goto('https://grnh.se/b6ff87e61us', wait_until='load', timeout=30000)
    print(f"Response status: {response.status if response else 'None'}")
    print(f"Response URL: {response.url if response else 'None'}")
    print(f"Page URL: {page.url}")

    time.sleep(5)  # Wait for any JS redirects
    print(f"After 5s - Page URL: {page.url}")

    # Check page content
    try:
        body = page.inner_text('body')[:1000]
        print(f"\nPage body ({len(body)} chars):")
        print(body)
    except Exception as e:
        print(f"Body error: {e}")

    # Check for any links
    links = page.locator('a').all()
    print(f"\nFound {len(links)} links")
    for link in links[:10]:
        try:
            href = link.get_attribute('href') or ''
            text = link.inner_text()[:50]
            print(f"  Link: {text} -> {href[:100]}")
        except:
            pass

    # Screenshot
    page.screenshot(path='/app/grnh_test.png')
    print("\nScreenshot saved to /app/grnh_test.png")

    browser.close()
