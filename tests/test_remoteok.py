"""Check what RemoteOK job page looks like."""
import os, django, time
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    )
    page = context.new_page()
    page.goto('https://remoteOK.com/remote-jobs/remote-software-engineer-ren-1130024', wait_until='load', timeout=20000)
    time.sleep(3)

    print(f"URL: {page.url}")

    # Find all links with "apply" text
    apply_links = page.locator('a').all()
    print(f"\nAll links ({len(apply_links)}):")
    for link in apply_links:
        try:
            href = link.get_attribute('href') or ''
            text = link.inner_text()[:40].strip()
            classes = link.get_attribute('class') or ''
            if 'apply' in text.lower() or 'apply' in href.lower() or 'apply' in classes.lower():
                print(f"  APPLY: '{text}' -> {href[:100]} class={classes[:50]}")
            elif href and not href.startswith('#') and not href.startswith('/'):
                print(f"  EXT: '{text}' -> {href[:100]}")
        except:
            pass

    # Check for buttons
    buttons = page.locator('button').all()
    for btn in buttons:
        try:
            text = btn.inner_text()[:40].strip()
            if 'apply' in text.lower():
                print(f"  BTN: '{text}'")
        except:
            pass

    # Check for iframes
    iframes = page.locator('iframe').all()
    for iframe in iframes:
        src = iframe.get_attribute('src') or ''
        if src:
            print(f"  IFRAME: {src[:100]}")

    browser.close()
