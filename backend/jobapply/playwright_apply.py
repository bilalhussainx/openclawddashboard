"""
Career page automation for job applications using Playwright.
Focuses on company career pages (Greenhouse, Lever, Workday, Ashby, etc.)
where no login is required and bot detection is minimal.

Strategy:
- If job URL is LinkedIn/Indeed, follow "Apply on company site" to the career page
- Detect which ATS the career page uses
- Fill the form with resume data and upload resume PDF
- Submit the application

This avoids automating LinkedIn/Indeed directly (which requires login and
triggers bot detection/account bans).
"""
import logging
import os
import random
import time

logger = logging.getLogger(__name__)


def _handle_greenhouse_security_code(page, user_id, _log) -> dict:
    """
    Handle Greenhouse security code verification by fetching code from Gmail.
    Polls Gmail for up to 2 minutes looking for the verification code.

    Returns:
        dict with 'success', 'method', 'error' keys
    """
    if not user_id:
        _log('security_code', 'no_user', 'Cannot fetch Gmail code - user_id not provided')
        return {
            'success': True,  # Form was submitted
            'method': 'greenhouse_pending_verification',
            'error': 'Application submitted - check email for security code verification (Gmail not connected)'
        }

    try:
        from google_integration.gmail_service import fetch_greenhouse_verification_code
    except ImportError:
        _log('security_code', 'import_error', 'Gmail service not available')
        return {
            'success': True,
            'method': 'greenhouse_pending_verification',
            'error': 'Application submitted - check email for security code verification'
        }

    _log('security_code', 'waiting', 'Waiting for verification code email...')

    # Poll for verification code (max 2 minutes = 24 attempts * 5 seconds)
    for attempt in range(24):
        code = fetch_greenhouse_verification_code(user_id, max_age_minutes=3)
        if code:
            _log('security_code', 'found', f'Got code from Gmail: {code[:2]}****')

            # Find and fill the verification input
            # Greenhouse typically uses a specific input for the code
            code_selectors = [
                'input[name*="security"]',
                'input[name*="code"]',
                'input[placeholder*="code"]',
                'input[aria-label*="code"]',
                'input[type="text"]:visible',  # Fallback to visible text input
            ]

            for selector in code_selectors:
                try:
                    code_input = page.locator(selector).first
                    if code_input.is_visible(timeout=1000):
                        code_input.fill(code)
                        _log('security_code', 'filled', f'Entered code in {selector}')

                        # Find and click submit/verify button
                        submit_selectors = [
                            'button[type="submit"]',
                            'button:has-text("Verify")',
                            'button:has-text("Submit")',
                            'button:has-text("Continue")',
                            'input[type="submit"]',
                        ]

                        for btn_selector in submit_selectors:
                            try:
                                btn = page.locator(btn_selector).first
                                if btn.is_visible(timeout=1000):
                                    btn.click()
                                    _log('security_code', 'submitted', 'Clicked verify button')
                                    time.sleep(3)

                                    # Check for success
                                    body = page.locator('body').inner_text()[:500].lower()
                                    if 'thank' in body or 'received' in body or 'submitted' in body or 'success' in body:
                                        _log('security_code', 'verified', 'Application verified successfully!')
                                        return {
                                            'success': True,
                                            'method': 'greenhouse_verified',
                                            'error': None
                                        }
                                    break
                            except Exception:
                                continue
                        break
                except Exception:
                    continue

            # If we got here, we found and entered the code but couldn't confirm success
            return {
                'success': True,
                'method': 'greenhouse_code_entered',
                'error': 'Verification code entered - please verify application was received'
            }

        # Wait before next attempt
        _log('security_code', 'polling', f'Attempt {attempt + 1}/24 - no code yet, waiting 5s...')
        time.sleep(5)

    # Timed out waiting for code
    _log('security_code', 'timeout', 'Verification code not received within 2 minutes')
    return {
        'success': True,
        'method': 'greenhouse_pending_verification',
        'error': 'Application submitted but verification code not received - check email manually'
    }


# ATS detection patterns: (url_substring, ats_name)
ATS_PATTERNS = [
    ('boards.greenhouse.io', 'greenhouse'),
    ('job-boards.greenhouse.io', 'greenhouse'),
    ('grnh.se', 'greenhouse'),
    ('greenhouse.io', 'greenhouse'),
    ('jobs.lever.co', 'lever'),
    ('lever.co', 'lever'),
    ('myworkdayjobs.com', 'workday'),
    ('ashbyhq.com', 'ashby'),
    ('jobs.ashby.com', 'ashby'),
    ('smartrecruiters.com', 'smartrecruiters'),
    ('bamboohr.com', 'bamboohr'),
    ('icims.com', 'icims'),
    ('jobvite.com', 'jobvite'),
    ('recruitee.com', 'recruitee'),
    ('breezy.hr', 'breezy'),
    ('applytojob.com', 'applytojob'),
    ('dover.com', 'dover'),
    ('rippling.com', 'rippling'),
]


def detect_ats(url: str) -> str:
    """Detect which ATS a URL belongs to."""
    url_lower = url.lower()
    for pattern, ats_name in ATS_PATTERNS:
        if pattern in url_lower:
            return ats_name
    return 'generic'


def apply_to_job_with_playwright(
    job_url: str,
    resume_data: dict,
    cover_letter: str = '',
    resume_file_path: str = '',
    user_id: int = None,
) -> dict:
    """
    Apply to a job via the company's career page using Playwright.
    If the URL is LinkedIn/Indeed, follows the "Apply on company site" link first.
    Returns {success, method, log, error}

    Args:
        job_url: URL of the job listing
        resume_data: Parsed resume data dict
        cover_letter: Generated cover letter text
        resume_file_path: Path to resume PDF for upload
        user_id: User ID for Gmail verification code fetching (optional)
    """
    from playwright.sync_api import sync_playwright

    log = []

    def _log(step, action, result):
        entry = {'step': step, 'action': action, 'result': result, 'timestamp': time.time()}
        log.append(entry)
        logger.info(f"[{step}] {action}: {result}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ]
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/122.0.0.0 Safari/537.36'
                ),
            )

            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)

            page = context.new_page()

            _log('navigate', 'open_url', f'Navigating to {job_url}')
            page.goto(job_url, wait_until='load', timeout=30000)
            _random_delay(2, 4)

            # Wait for any JS/meta redirects to complete
            current_url = page.url
            if current_url == job_url:
                # May have a JS redirect pending - wait briefly
                try:
                    page.wait_for_url('**', timeout=5000)
                except Exception:
                    pass
                current_url = page.url

            _log('navigate', 'page_loaded', f'Page loaded: {current_url}')

            # If on LinkedIn/Indeed, extract the company career page URL
            career_url = _extract_career_page_url(page, current_url, _log)
            if career_url and career_url != current_url:
                _log('redirect', 'career_page', f'Following to career page: {career_url}')
                page.goto(career_url, wait_until='domcontentloaded', timeout=30000)
                _random_delay(2, 4)
                current_url = page.url
                _log('redirect', 'arrived', f'Career page loaded: {current_url}')

            # If we're still on LinkedIn/Indeed, we can't apply without login
            if _is_job_board(current_url):
                board_name = 'this job board'
                for name in ['LinkedIn', 'Indeed', 'Glassdoor', 'RemoteOK']:
                    if name.lower() in current_url.lower():
                        board_name = name
                        break
                _log('skip', 'job_board', f'Still on {board_name} - cannot apply without login')
                browser.close()
                return {
                    'success': False,
                    'method': 'manual_apply',
                    'log': log,
                    'error': f'This job is on {board_name} which requires login to apply. Your cover letter was generated - open the link and apply manually.',
                }

            # Detect ATS and route to handler
            ats = detect_ats(current_url)
            _log('detect', 'ats', f'Detected ATS: {ats}')

            if ats == 'greenhouse':
                result = _apply_greenhouse(page, resume_data, cover_letter, resume_file_path, _log, user_id)
            elif ats == 'lever':
                result = _apply_lever(page, resume_data, cover_letter, resume_file_path, _log)
            elif ats == 'workday':
                result = _apply_workday(page, resume_data, cover_letter, resume_file_path, _log)
            elif ats == 'ashby':
                result = _apply_ashby(page, resume_data, cover_letter, resume_file_path, _log)
            elif ats == 'smartrecruiters':
                result = _apply_smartrecruiters(page, resume_data, cover_letter, resume_file_path, _log)
            else:
                result = _apply_generic(page, resume_data, cover_letter, resume_file_path, _log)

            browser.close()
            result['log'] = log
            return result

    except Exception as e:
        logger.error(f"Career page apply failed: {e}")
        return {
            'success': False,
            'method': 'error',
            'log': log,
            'error': str(e),
        }


def _is_job_board(url: str) -> bool:
    """Check if the URL is a job board (not a company career page)."""
    url_lower = url.lower()
    return any(board in url_lower for board in [
        'linkedin.com', 'indeed.com', 'glassdoor.com', 'remoteok.com',
    ])


def _random_delay(min_sec=1, max_sec=3):
    """Human-like random delay."""
    time.sleep(random.uniform(min_sec, max_sec))


def _extract_career_page_url(page, current_url: str, _log) -> str:
    """
    If on LinkedIn/Indeed, find the "Apply on company site" link
    and return the career page URL. Returns current_url if already on a career page.
    """
    url_lower = current_url.lower()

    if 'linkedin.com' in url_lower:
        _log('extract', 'linkedin', 'On LinkedIn - looking for company apply link')

        # Look for "Apply on company website" style links
        for selector in [
            'a:has-text("Apply on company")',
            'a:has-text("Apply on")',
            'a[data-tracking-control-name*="company_website"]',
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=3000):
                    href = el.get_attribute('href') or ''
                    if href and 'linkedin.com' not in href.lower():
                        _log('extract', 'found_link', f'Found career page: {href}')
                        return href
            except Exception:
                continue

        # Try clicking Apply to see if it redirects externally
        try:
            apply_btn = page.locator('button:has-text("Apply")').first
            if apply_btn.is_visible(timeout=2000):
                # Listen for new page (popup)
                with page.context.expect_page(timeout=8000) as new_page_info:
                    apply_btn.click()
                try:
                    new_page = new_page_info.value
                    new_url = new_page.url
                    if not _is_job_board(new_url):
                        _log('extract', 'popup_redirect', f'Redirected to: {new_url}')
                        # Navigate main page to career URL and close popup
                        new_page.close()
                        return new_url
                    new_page.close()
                except Exception:
                    _random_delay(2, 3)
                    if not _is_job_board(page.url):
                        return page.url
        except Exception:
            pass

        _log('extract', 'no_redirect', 'No company career page found from LinkedIn')
        return current_url

    elif 'indeed.com' in url_lower:
        _log('extract', 'indeed', 'On Indeed - looking for company apply link')

        for selector in [
            'a:has-text("Apply on company site")',
            'button:has-text("Apply on company site")',
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=3000):
                    href = el.get_attribute('href') or ''
                    if href and 'indeed.com' not in href.lower():
                        return href
                    # Try clicking it
                    el.click()
                    _random_delay(3, 5)
                    if not _is_job_board(page.url):
                        return page.url
            except Exception:
                continue

        _log('extract', 'no_redirect', 'No company career page found from Indeed')
        return current_url

    elif 'remoteok.com' in url_lower:
        _log('extract', 'remoteok', 'On RemoteOK - searching for company career page')
        import re

        # RemoteOK requires login for /l/ apply links (they redirect to sign-up page).
        # Strategy: find the "Careers Site" link in the expanded job section,
        # or find any external link that points to the company career page.

        # Extract job ID from URL for targeting the right expand section
        job_id_match = re.search(r'-(\d+)$', current_url)
        career_page = None

        if job_id_match:
            job_id = job_id_match.group(1)
            expand_selector = f'.expand-{job_id}'

            # The job page auto-expands the target job - look for links in its section
            try:
                expand_el = page.locator(expand_selector)
                if expand_el.count():
                    links = expand_el.locator('a').all()
                    for link in links:
                        try:
                            href = link.get_attribute('href') or ''
                            text = (link.inner_text() or '').strip().lower()
                            # "Careers Site" links go directly to company career pages
                            if 'career' in text and href.startswith('http') and 'remoteok' not in href.lower():
                                career_page = href
                                _log('extract', 'remoteok_careers', f'Found Careers Site link: {href}')
                                break
                        except Exception:
                            continue

                    # If no "Careers Site" link, look for any external link (not remoteok, not rok.co)
                    if not career_page:
                        for link in links:
                            try:
                                href = link.get_attribute('href') or ''
                                if (href.startswith('http')
                                        and 'remoteok' not in href.lower()
                                        and 'rok.co' not in href.lower()
                                        and '/l/' not in href):
                                    # Could be company website - check if it has career/jobs path
                                    if any(kw in href.lower() for kw in ['career', 'jobs', 'greenhouse', 'lever', 'workday', 'ashby', 'apply']):
                                        career_page = href
                                        _log('extract', 'remoteok_ext_career', f'Found external career link: {href}')
                                        break
                            except Exception:
                                continue
            except Exception as e:
                _log('extract', 'remoteok_expand_error', str(e))

        # Also check for any external link with company name that might be their website
        if not career_page:
            try:
                expand_el = page.locator(expand_selector) if job_id_match else None
                if expand_el and expand_el.count():
                    links = expand_el.locator('a').all()
                    for link in links:
                        try:
                            href = link.get_attribute('href') or ''
                            if (href.startswith('http')
                                    and 'remoteok' not in href.lower()
                                    and 'rok.co' not in href.lower()
                                    and '/l/' not in href):
                                # This is a company website link - try appending /careers
                                _log('extract', 'remoteok_company_site', f'Found company site: {href}')
                                # Navigate to company site and look for careers/jobs page
                                page.goto(href, wait_until='load', timeout=15000)
                                _random_delay(1, 2)
                                # Look for careers/jobs link on company site
                                for career_sel in ['a:has-text("Careers")', 'a:has-text("Jobs")', 'a:has-text("Work with us")', 'a[href*="career"]', 'a[href*="jobs"]']:
                                    try:
                                        career_link = page.locator(career_sel).first
                                        if career_link.is_visible(timeout=2000):
                                            career_href = career_link.get_attribute('href') or ''
                                            if career_href:
                                                if not career_href.startswith('http'):
                                                    career_href = href.rstrip('/') + '/' + career_href.lstrip('/')
                                                career_page = career_href
                                                _log('extract', 'remoteok_company_careers', f'Found careers page: {career_page}')
                                                break
                                    except Exception:
                                        continue
                                if career_page:
                                    break
                        except Exception:
                            continue
            except Exception as e:
                _log('extract', 'remoteok_company_error', str(e))

        if career_page:
            _log('extract', 'remoteok_navigate', f'Navigating to career page: {career_page}')
            page.goto(career_page, wait_until='load', timeout=20000)
            _random_delay(2, 4)
            return page.url

        _log('extract', 'no_redirect', 'Could not find company career page from RemoteOK')
        return current_url

    # Already on a career page
    return current_url


def _upload_resume(page, resume_file_path: str, _log) -> bool:
    """Find file input and upload resume PDF. Returns True if uploaded."""
    if not resume_file_path or not os.path.exists(resume_file_path):
        _log('upload', 'no_file', f'Resume file not available: {resume_file_path}')
        return False

    # Find file input elements (including hidden ones used by dropzones)
    file_inputs = page.locator('input[type="file"]').all()
    for fi in file_inputs:
        try:
            fi.set_input_files(resume_file_path)
            _log('upload', 'success', f'Uploaded resume: {os.path.basename(resume_file_path)}')
            _random_delay(2, 3)
            return True
        except Exception as e:
            _log('upload', 'error', str(e))

    _log('upload', 'no_input', 'No file upload input found on page')
    return False


def _fill_text_field(page, selectors: list, value: str, _log, field_name: str) -> bool:
    """Try multiple selectors to fill a text field. Returns True if filled."""
    if not value:
        return False
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=2000):
                el.fill(value)
                _log('fill', field_name, f'Filled "{field_name}"')
                _random_delay(0.3, 0.8)
                return True
        except Exception:
            continue
    return False


def _click_submit(page, _log, method: str) -> dict:
    """Find and click the submit/apply button."""
    _random_delay(1, 2)

    for selector in [
        'button:has-text("Submit Application")',
        'button:has-text("Submit application")',
        'button:has-text("Submit")',
        'button:has-text("Apply")',
        'button:has-text("Apply Now")',
        'button:has-text("Send Application")',
        'button:has-text("Complete Application")',
        'input[type="submit"]',
        'button[type="submit"]',
    ]:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=2000):
                _log('submit', 'clicking', f'Clicking: {selector}')
                btn.click()
                _random_delay(3, 5)

                # Check for success indicators on the page
                try:
                    body_text = page.inner_text('body')[:3000].lower()
                    success_phrases = [
                        'application submitted', 'thank you for applying',
                        'thanks for applying', 'application received',
                        'successfully submitted', 'we received your application',
                        'application has been submitted', 'you have applied',
                    ]
                    if any(phrase in body_text for phrase in success_phrases):
                        _log('submit', 'confirmed', 'Success confirmed on page')
                        return {'success': True, 'method': method, 'error': None}

                    # Check for Greenhouse security code verification
                    if 'security code' in body_text or 'verification code' in body_text:
                        _log('submit', 'security_code', 'Greenhouse requires email security code verification - check your email')
                        return {
                            'success': True,
                            'method': method,
                            'error': 'Application submitted but requires email verification. Check your email for a security code from Greenhouse.',
                        }
                except Exception:
                    pass

                _log('submit', 'clicked', 'Submit button clicked')
                return {'success': True, 'method': method, 'error': None}
        except Exception:
            continue

    _log('submit', 'not_found', 'No submit button found')
    return {'success': False, 'method': method, 'error': 'No submit button found'}


# ──────────────────────────────────────────────────────────────
# ATS-specific handlers
# ──────────────────────────────────────────────────────────────

def _greenhouse_select_dropdown(page, input_el, target_text, _log, field_name=''):
    """Click a Greenhouse select__input to open dropdown and pick an option.

    Greenhouse custom dropdowns support typing to filter options.
    Strategy: click input, type the target text, then select the matching option.
    """
    try:
        # Click input to open dropdown
        input_el.click()
        _random_delay(0.3, 0.5)

        if target_text:
            # Type the answer to filter the dropdown options
            input_el.fill(target_text)
            _random_delay(0.5, 0.8)

        # Find visible options - prefer the ones in the currently active dropdown
        options = page.locator('[role="option"]:visible').all()
        if not options:
            _random_delay(0.3, 0.5)
            options = page.locator('[role="option"]').all()

        if not options:
            input_el.press('Escape')
            return False

        target_lower = target_text.lower() if target_text else ''

        # Search from the end (custom options appear after country codes in Greenhouse)
        best_match = None
        for opt in reversed(options):
            try:
                opt_text = (opt.inner_text() or '').strip()
                opt_lower = opt_text.lower()
                if not opt_text:
                    continue
                # Exact match preferred
                if target_lower and (opt_lower == target_lower or target_lower == opt_lower):
                    best_match = opt
                    break
                # Partial match
                if target_lower and (target_lower in opt_lower or opt_lower.startswith(target_lower)):
                    best_match = opt
                    break
            except Exception:
                continue

        # If no match found with text search, just pick the last option (likely the actual answer, not a country code)
        if not best_match and target_text:
            # The actual Yes/No options appear at the end after country codes
            for opt in reversed(options):
                try:
                    opt_text = (opt.inner_text() or '').strip()
                    if opt_text and len(opt_text) < 30 and not any(c.isdigit() for c in opt_text[-3:]):
                        # Short text without trailing phone codes = likely the real option
                        best_match = opt
                        break
                except Exception:
                    continue

        if best_match:
            try:
                match_text = (best_match.inner_text() or '').strip()
                best_match.click()
                _log('fill', field_name, f'Selected "{match_text}"')
                _random_delay(0.2, 0.4)
                return True
            except Exception:
                pass

        # Fallback: select first non-country option (short text at end of list)
        if not target_text:
            for opt in reversed(options):
                try:
                    opt_text = (opt.inner_text() or '').strip()
                    if opt_text and len(opt_text) < 50:
                        opt.click()
                        _log('fill', field_name + '_default', f'Selected "{opt_text}"')
                        _random_delay(0.2, 0.4)
                        return True
                except Exception:
                    continue

        input_el.press('Escape')
    except Exception as e:
        _log('fill', field_name + '_error', str(e)[:80])
    return False


def _fill_greenhouse_custom_fields(page, resume_data, cover_letter, _log):
    """Fill custom/required fields on Greenhouse forms (country, dropdowns, textareas)."""
    data = resume_data or {}
    filled = 0

    # Keyword-based answers for dropdown questions
    # ORDER MATTERS: more specific keywords must come first to avoid false matches
    # (e.g., "visa sponsorship" contains "country" if label says "work in the country")
    DROPDOWN_ANSWERS = [
        ('visa sponsorship', 'No'),
        ('visa sponsor', 'No'),
        ('require.*visa', 'No'),
        ('sponsorship', 'No'),
        ('visa', 'No'),
        ('interviewed before', 'No'),
        ('interviewed at', 'No'),
        ('authorized to work', 'I am authorized to work in the country d'),
        ('authorization to work', 'I am authorized to work in the country d'),
        ('legally authorized', 'I am authorized to work in the country d'),
        ('relocation', 'Yes'),
        ('in-person', 'Yes'),
        ('in person', 'Yes'),
        ('office', 'Yes'),
        ('hear about', 'Job board'),
        ('policy', 'Yes'),
        ('country', 'Canada'),  # Must be LAST since many labels contain "country"
    ]

    # Skip these fields (sensitive demographics)
    SKIP_LABELS = ['gender', 'race', 'ethnicity', 'hispanic', 'veteran', 'disability', 'pronouns']

    # Process all labels on the form
    labels = page.locator('label').all()
    for lab in labels:
        try:
            text = (lab.inner_text() or '').strip()
            if not text or len(text) < 3:
                continue

            text_lower = text.lower()
            is_required = '*' in text
            for_id = lab.get_attribute('for') or ''

            if not for_id:
                continue

            # Skip demographic/sensitive fields
            if any(skip in text_lower for skip in SKIP_LABELS):
                continue

            # Skip already-filled standard fields
            if for_id in ('first_name', 'last_name', 'email', 'phone', 'resume', 'cover_letter', 'resume_text', 'cover_letter_text'):
                continue

            # Get the associated input element
            assoc = page.locator(f'#{for_id}')
            if not assoc.count():
                continue
            # Scroll into view to ensure visibility
            try:
                assoc.scroll_into_view_if_needed(timeout=2000)
                _random_delay(0.2, 0.3)
            except Exception:
                pass
            if not assoc.is_visible(timeout=1000):
                continue

            classes = assoc.get_attribute('class') or ''
            tag = assoc.evaluate('el => el.tagName')

            # Handle select__input (Greenhouse custom dropdown)
            if 'select__input' in classes:
                # Determine the answer based on label text (order matters - more specific first)
                import re as _re
                answer = None
                for keyword, default_answer in DROPDOWN_ANSWERS:
                    if '.*' in keyword:
                        if _re.search(keyword, text_lower):
                            answer = default_answer
                            break
                    elif keyword in text_lower:
                        answer = default_answer
                        break

                if answer:
                    if _greenhouse_select_dropdown(page, assoc, answer, _log, for_id):
                        filled += 1
                elif is_required:
                    # Required but unknown dropdown - select first option
                    if _greenhouse_select_dropdown(page, assoc, '', _log, for_id):
                        filled += 1

            # Handle textarea
            elif tag == 'TEXTAREA':
                if 'why' in text_lower and is_required:
                    value = cover_letter[:500] if cover_letter else (
                        f"I am passionate about this opportunity and believe my experience "
                        f"as a developer in {data.get('location', 'Toronto')} aligns well with this role."
                    )
                    assoc.fill(value)
                    _log('fill', for_id, f'Filled textarea: {text[:40]}')
                    filled += 1
                elif is_required:
                    assoc.fill('N/A')
                    _log('fill', for_id, f'Filled N/A: {text[:40]}')
                    filled += 1

            # Handle text inputs for known fields
            elif tag == 'INPUT' and 'select__input' not in classes:
                if 'linkedin' in text_lower and data.get('linkedin'):
                    assoc.fill(data['linkedin'])
                    _log('fill', for_id, 'Filled LinkedIn')
                    filled += 1
                elif 'github' in text_lower and data.get('github'):
                    assoc.fill(data['github'])
                    _log('fill', for_id, 'Filled GitHub')
                    filled += 1
                elif 'website' in text_lower and data.get('github'):
                    assoc.fill(data['github'])
                    _log('fill', for_id, 'Filled website with GitHub')
                    filled += 1
                elif ('earliest' in text_lower or 'start' in text_lower) and 'date' not in classes:
                    assoc.fill('As soon as possible')
                    _log('fill', for_id, 'Filled start date')
                    filled += 1
                elif 'address' in text_lower:
                    assoc.fill(data.get('location', 'Toronto, Ontario'))
                    _log('fill', for_id, 'Filled address')
                    filled += 1

        except Exception:
            continue

    return filled


def _apply_greenhouse(page, resume_data, cover_letter, resume_file_path, _log, user_id=None) -> dict:
    """Greenhouse ATS - very common, predictable form structure."""
    _log('greenhouse', 'start', 'Applying via Greenhouse')
    data = resume_data or {}
    filled = 0

    name = data.get('name', '')
    first_name = name.split()[0] if name else ''
    last_name = name.split()[-1] if name and len(name.split()) > 1 else ''

    if _fill_text_field(page, [
        '#first_name', 'input[name="job_application[first_name]"]',
        'input[autocomplete="given-name"]',
    ], first_name, _log, 'first_name'):
        filled += 1

    if _fill_text_field(page, [
        '#last_name', 'input[name="job_application[last_name]"]',
        'input[autocomplete="family-name"]',
    ], last_name, _log, 'last_name'):
        filled += 1

    if _fill_text_field(page, [
        '#email', 'input[name="job_application[email]"]',
        'input[type="email"]',
    ], data.get('email', ''), _log, 'email'):
        filled += 1

    if _fill_text_field(page, [
        '#phone', 'input[name="job_application[phone]"]',
        'input[type="tel"]',
    ], data.get('phone', ''), _log, 'phone'):
        filled += 1

    if _fill_text_field(page, [
        '#job_application_location',
        'input[name="job_application[location]"]',
    ], data.get('location', ''), _log, 'location'):
        filled += 1

    _upload_resume(page, resume_file_path, _log)

    if cover_letter:
        _fill_text_field(page, [
            '#cover_letter',
            'textarea[name="job_application[cover_letter]"]',
            'textarea[id*="cover"]',
        ], cover_letter, _log, 'cover_letter')

    linkedin = data.get('linkedin', '')
    if linkedin:
        _fill_text_field(page, [
            'input[name*="linkedin"]', 'input[id*="linkedin"]',
            'input[placeholder*="LinkedIn"]',
        ], linkedin, _log, 'linkedin')

    github = data.get('github', '')
    if github:
        _fill_text_field(page, [
            'input[name*="github"]', 'input[id*="github"]',
            'input[placeholder*="GitHub"]',
        ], github, _log, 'github')

    # Fill custom/required fields (country, dropdowns, custom questions)
    _fill_greenhouse_custom_fields(page, data, cover_letter, _log)
    _random_delay(1, 2)

    if filled >= 2:
        result = _click_submit(page, _log, 'greenhouse')

        # Verify submission: check for errors after submit
        _random_delay(2, 3)
        try:
            errors = page.locator('.field-error, [class*="error"]').all()
            error_texts = []
            for err in errors:
                text = (err.inner_text() or '').strip()
                if text and 'required' in text.lower():
                    error_texts.append(text[:60])
            if error_texts:
                _log('greenhouse', 'validation_errors', f'Found {len(error_texts)} errors, retrying unfilled dropdowns')

                # RETRY: find and fill any remaining empty select__input fields
                try:
                    empty_selects = page.locator('input.select__input').all()
                    for sel in empty_selects:
                        try:
                            if not sel.is_visible(timeout=500):
                                continue
                            val = sel.input_value() or ''
                            if val:
                                continue  # Already filled
                            sel.scroll_into_view_if_needed(timeout=1000)
                            _random_delay(0.2, 0.3)
                            # Select first option
                            _greenhouse_select_dropdown(page, sel, '', _log, 'retry_dropdown')
                        except Exception:
                            continue
                except Exception:
                    pass

                _random_delay(1, 2)

                # Re-submit
                _log('greenhouse', 'resubmit', 'Resubmitting after filling missed fields')
                result2 = _click_submit(page, _log, 'greenhouse')
                _random_delay(2, 3)

                # Check for errors again
                try:
                    errors2 = page.locator('.field-error, [class*="error"]').all()
                    error_texts2 = []
                    for err in errors2:
                        text = (err.inner_text() or '').strip()
                        if text and 'required' in text.lower():
                            error_texts2.append(text[:60])
                    if error_texts2:
                        result2['error'] = f'Form has unfilled required fields: {", ".join(error_texts2[:3])}'
                        result2['success'] = False
                        _log('greenhouse', 'still_errors', result2['error'])
                    else:
                        body = page.locator('body').inner_text()[:500].lower()
                        if 'security code' in body or 'verification code' in body:
                            # Try to fetch and enter verification code from Gmail
                            gmail_result = _handle_greenhouse_security_code(page, user_id, _log)
                            result2.update(gmail_result)
                        elif 'thank' in body or 'received' in body or 'submitted' in body:
                            _log('greenhouse', 'confirmed', 'Application confirmed on retry')
                            result2['success'] = True
                except Exception:
                    pass

                return result2
            else:
                # Check for success indicators
                body = page.locator('body').inner_text()[:500].lower()
                if 'security code' in body or 'verification code' in body:
                    # Try to fetch and enter verification code from Gmail
                    gmail_result = _handle_greenhouse_security_code(page, user_id, _log)
                    result.update(gmail_result)
                elif 'thank' in body or 'received' in body or 'submitted' in body:
                    _log('greenhouse', 'confirmed', 'Application confirmed - thank you page detected')
                    result['success'] = True
        except Exception:
            pass

        return result

    return {'success': False, 'method': 'greenhouse', 'error': f'Only filled {filled} fields'}


def _apply_lever(page, resume_data, cover_letter, resume_file_path, _log) -> dict:
    """Lever ATS - "Apply for this job" button, then form."""
    _log('lever', 'start', 'Applying via Lever')
    data = resume_data or {}
    filled = 0

    # Lever has an "Apply for this job" button on the job description page
    try:
        apply_btn = page.locator(
            'a:has-text("Apply for this job"), '
            'button:has-text("Apply for this job"), '
            'a.postings-btn'
        ).first
        if apply_btn.is_visible(timeout=3000):
            apply_btn.click()
            _random_delay(2, 3)
    except Exception:
        pass

    name = data.get('name', '')
    if _fill_text_field(page, [
        'input[name="name"]', '#name-input',
        'input[placeholder*="Full name"]',
    ], name, _log, 'name'):
        filled += 1

    if _fill_text_field(page, [
        'input[name="email"]', '#email-input',
        'input[type="email"]',
    ], data.get('email', ''), _log, 'email'):
        filled += 1

    if _fill_text_field(page, [
        'input[name="phone"]', '#phone-input',
        'input[type="tel"]',
    ], data.get('phone', ''), _log, 'phone'):
        filled += 1

    current_company = ''
    if data.get('experience'):
        current_company = data['experience'][0].get('company', '')
    if _fill_text_field(page, [
        'input[name="org"]', '#org-input',
        'input[placeholder*="Current company"]',
    ], current_company, _log, 'company'):
        filled += 1

    _upload_resume(page, resume_file_path, _log)

    if cover_letter:
        _fill_text_field(page, [
            'textarea[name="comments"]',
            '#additional-information',
            'textarea[placeholder*="Add a cover letter"]',
        ], cover_letter, _log, 'cover_letter')

    linkedin = data.get('linkedin', '')
    if linkedin:
        _fill_text_field(page, [
            'input[name*="urls[LinkedIn]"]',
            'input[placeholder*="LinkedIn"]',
        ], linkedin, _log, 'linkedin')

    if filled >= 2:
        return _click_submit(page, _log, 'lever')

    return {'success': False, 'method': 'lever', 'error': f'Only filled {filled} fields'}


def _apply_workday(page, resume_data, cover_letter, resume_file_path, _log) -> dict:
    """Workday ATS - multi-step, can auto-parse resume."""
    _log('workday', 'start', 'Applying via Workday')
    data = resume_data or {}

    # Workday often shows Apply button first
    try:
        apply_btn = page.locator(
            'button:has-text("Apply"), a:has-text("Apply")'
        ).first
        if apply_btn.is_visible(timeout=5000):
            apply_btn.click()
            _random_delay(3, 5)
    except Exception:
        pass

    # Try "Apply Manually" if there's a choice (vs sign in)
    try:
        manual = page.locator(
            'button:has-text("Apply Manually"), '
            'a:has-text("Apply Manually"), '
            'button:has-text("Apply Without")'
        ).first
        if manual.is_visible(timeout=3000):
            manual.click()
            _random_delay(2, 3)
    except Exception:
        pass

    # Upload resume first - Workday often auto-fills from it
    uploaded = _upload_resume(page, resume_file_path, _log)
    if uploaded:
        _random_delay(4, 6)  # Wait for Workday to parse the resume

    filled = _fill_form_fields_generic(page, data, _log)

    if cover_letter:
        _fill_text_field(page, [
            'textarea[data-automation-id*="cover"]',
            'textarea[aria-label*="Cover Letter"]',
            'textarea[placeholder*="cover letter"]',
        ], cover_letter, _log, 'cover_letter')

    if filled >= 2 or uploaded:
        return _click_submit(page, _log, 'workday')

    return {'success': False, 'method': 'workday', 'error': 'Could not fill Workday form'}


def _apply_ashby(page, resume_data, cover_letter, resume_file_path, _log) -> dict:
    """Ashby ATS - modern, clean forms."""
    _log('ashby', 'start', 'Applying via Ashby')
    data = resume_data or {}
    filled = 0

    name = data.get('name', '')
    first_name = name.split()[0] if name else ''
    last_name = name.split()[-1] if name and len(name.split()) > 1 else ''

    if _fill_text_field(page, [
        'input[name="firstName"]', 'input[placeholder*="First"]',
    ], first_name, _log, 'first_name'):
        filled += 1

    if _fill_text_field(page, [
        'input[name="lastName"]', 'input[placeholder*="Last"]',
    ], last_name, _log, 'last_name'):
        filled += 1

    if _fill_text_field(page, [
        'input[name="email"]', 'input[type="email"]',
    ], data.get('email', ''), _log, 'email'):
        filled += 1

    if _fill_text_field(page, [
        'input[name="phone"]', 'input[type="tel"]',
    ], data.get('phone', ''), _log, 'phone'):
        filled += 1

    _upload_resume(page, resume_file_path, _log)

    if cover_letter:
        _fill_text_field(page, [
            'textarea[name="coverLetter"]',
            'textarea[placeholder*="cover letter"]',
        ], cover_letter, _log, 'cover_letter')

    if filled >= 2:
        return _click_submit(page, _log, 'ashby')

    return {'success': False, 'method': 'ashby', 'error': f'Only filled {filled} fields'}


def _apply_smartrecruiters(page, resume_data, cover_letter, resume_file_path, _log) -> dict:
    """SmartRecruiters ATS."""
    _log('smartrecruiters', 'start', 'Applying via SmartRecruiters')
    data = resume_data or {}

    try:
        apply_btn = page.locator(
            'button:has-text("Apply Now"), a:has-text("Apply")'
        ).first
        if apply_btn.is_visible(timeout=3000):
            apply_btn.click()
            _random_delay(2, 4)
    except Exception:
        pass

    _upload_resume(page, resume_file_path, _log)
    _random_delay(2, 3)

    filled = _fill_form_fields_generic(page, data, _log)

    if cover_letter:
        _fill_text_field(page, [
            'textarea[name*="coverLetter"]',
            'textarea[aria-label*="Cover"]',
        ], cover_letter, _log, 'cover_letter')

    if filled >= 2:
        return _click_submit(page, _log, 'smartrecruiters')

    return {'success': False, 'method': 'smartrecruiters', 'error': f'Only filled {filled} fields'}


def _apply_generic(page, resume_data, cover_letter, resume_file_path, _log) -> dict:
    """Generic career page - tries common form patterns."""
    _log('generic', 'start', 'Applying via generic career page')
    data = resume_data or {}

    # Look for an Apply button to open the form
    try:
        for selector in [
            'button:has-text("Apply")',
            'a:has-text("Apply")',
            'button:has-text("Apply Now")',
            'a:has-text("Apply Now")',
            'a:has-text("Apply for this")',
        ]:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=2000):
                btn.click()
                _random_delay(2, 4)
                break
    except Exception:
        pass

    _upload_resume(page, resume_file_path, _log)
    _random_delay(1, 2)

    filled = _fill_form_fields_generic(page, data, _log)

    # Fill cover letter into the first matching textarea
    if cover_letter:
        textareas = page.locator('textarea').all()
        for ta in textareas:
            try:
                if not ta.is_visible():
                    continue
                label = (
                    ta.get_attribute('aria-label') or
                    ta.get_attribute('placeholder') or
                    ta.get_attribute('name') or ''
                ).lower()
                if any(kw in label for kw in [
                    'cover', 'letter', 'message', 'additional', 'comment',
                ]):
                    ta.fill(cover_letter)
                    _log('fill', 'cover_letter', 'Filled cover letter')
                    _random_delay(0.5, 1)
                    break
            except Exception:
                continue

    if filled >= 2:
        return _click_submit(page, _log, 'generic')

    _log('generic', 'insufficient', f'Only filled {filled} fields')
    return {'success': False, 'method': 'generic', 'error': f'Only filled {filled} fields'}


# ──────────────────────────────────────────────────────────────
# Generic form field filler
# ──────────────────────────────────────────────────────────────

def _fill_form_fields_generic(page, resume_data: dict, _log) -> int:
    """Fill visible form fields by matching labels to resume data. Returns fill count."""
    filled = 0
    data = resume_data or {}

    name = data.get('name', '')
    first_name = name.split()[0] if name else ''
    last_name = name.split()[-1] if name and len(name.split()) > 1 else ''

    current_title = ''
    current_company = ''
    if data.get('experience'):
        current_title = data['experience'][0].get('title', '')
        current_company = data['experience'][0].get('company', '')

    field_map = [
        (['first name', 'given name', 'firstname', 'first_name', 'fname'], first_name),
        (['last name', 'family name', 'surname', 'lastname', 'last_name', 'lname'], last_name),
        (['full name', 'your name', 'fullname'], name),
        (['email', 'e-mail'], data.get('email', '')),
        (['phone', 'mobile', 'tel', 'telephone'], data.get('phone', '')),
        (['city', 'location', 'address'], data.get('location', '')),
        (['linkedin', 'linked in'], data.get('linkedin', '')),
        (['website', 'portfolio', 'github'], data.get('website', data.get('github', ''))),
        (['current title', 'job title', 'position', 'current role'], current_title),
        (['current company', 'employer', 'company name', 'organization'], current_company),
    ]

    inputs = page.locator(
        'input[type="text"], input[type="email"], input[type="tel"], '
        'input[type="url"], input:not([type])'
    ).all()

    for input_el in inputs:
        try:
            if not input_el.is_visible():
                continue
        except Exception:
            continue

        # Determine the label for this field
        label = ''
        try:
            label = input_el.get_attribute('aria-label') or ''
            if not label:
                label = input_el.get_attribute('placeholder') or ''
            if not label:
                input_id = input_el.get_attribute('id')
                if input_id:
                    try:
                        label_el = page.locator(f'label[for="{input_id}"]').first
                        if label_el.is_visible(timeout=500):
                            label = label_el.inner_text()
                    except Exception:
                        pass
            if not label:
                label = input_el.get_attribute('name') or ''
        except Exception:
            continue

        if not label:
            continue

        label_lower = label.lower().strip()

        for patterns, value in field_map:
            if any(pattern in label_lower for pattern in patterns):
                if value:
                    try:
                        input_el.fill(value)
                        filled += 1
                        _log('fill', f'filled_{label_lower[:20]}', f'Set "{label}"')
                        _random_delay(0.3, 0.8)
                    except Exception as e:
                        _log('fill', f'error_{label_lower[:20]}', str(e))
                break

    return filled
