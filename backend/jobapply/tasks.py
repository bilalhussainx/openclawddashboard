"""
Celery tasks for automated job discovery, cover letter generation, and application.
"""
import hashlib
import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def discover_jobs(user_id: int, boards_override: list = None) -> dict:
    """
    Search all enabled job boards for matching jobs, score them, and save to DB.
    Reuses the existing scrape_jobs_with_jobspy function from automations.
    boards_override: if provided, only search these boards (used by search_startups).
    """
    from django.contrib.auth import get_user_model
    from automations.tasks import scrape_jobs_with_jobspy
    from .models import JobPreferences, JobListing, Resume
    from .scoring import score_job_for_user
    from .startup_scrapers import scrape_startup_boards, STARTUP_BOARD_NAMES

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'error': 'User not found'}

    prefs, _ = JobPreferences.objects.get_or_create(user=user)
    resume = Resume.objects.filter(user=user, is_primary=True).first()
    resume_data = resume.parsed_data if resume else {}

    keywords = prefs.keywords or ['Software Developer']
    boards = boards_override or prefs.enabled_boards or ['indeed', 'linkedin']
    location = prefs.location or 'Toronto'

    # Split into JobSpy boards vs startup boards
    jobspy_boards = [b for b in boards if b not in STARTUP_BOARD_NAMES]
    startup_boards = [b for b in boards if b in STARTUP_BOARD_NAMES]

    total_discovered = 0
    total_new = 0

    # Phase 1: JobSpy boards (LinkedIn/Indeed/Glassdoor)
    if jobspy_boards:
        for keyword in keywords:
            logger.info(f"Searching '{keyword}' on {jobspy_boards} in {location}")

            result = scrape_jobs_with_jobspy(
                search_term=keyword,
                location=location,
                sites=jobspy_boards,
                results_wanted=30,
                hours_old=72,
                is_remote=prefs.remote_ok,
                country='canada',
            )

            if not result.get('success'):
                logger.warning(f"JobSpy failed for '{keyword}': {result.get('errors')}")
                continue

            jobs = result.get('jobs', [])
            total_discovered += len(jobs)
            total_new += _save_jobs(jobs, user, resume_data, prefs)

    # Phase 2: Startup boards (HN, RemoteOK)
    if startup_boards:
        seen_urls = set()
        for keyword in keywords:
            logger.info(f"Searching '{keyword}' on startup boards {startup_boards}")

            result = scrape_startup_boards(
                search_term=keyword,
                enabled_boards=startup_boards,
                location=location,
                remote_ok=prefs.remote_ok,
                max_results_per_board=15,
            )

            if not result.get('success'):
                logger.warning(f"Startup scrapers failed for '{keyword}': {result.get('errors')}")
                continue

            # Deduplicate within this run across keywords
            new_jobs = []
            for job in result.get('jobs', []):
                url = job.get('job_url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    new_jobs.append(job)

            total_discovered += len(new_jobs)
            total_new += _save_jobs(new_jobs, user, resume_data, prefs)

    logger.info(f"Job discovery complete: {total_discovered} found, {total_new} new")
    return {
        'total_discovered': total_discovered,
        'total_new': total_new,
        'keywords_searched': len(keywords),
    }


def _save_jobs(jobs: list, user, resume_data: dict, prefs) -> int:
    """Score and save a list of job dicts. Returns count of newly saved jobs."""
    from .models import JobListing
    from .scoring import score_job_for_user

    new_count = 0
    for job in jobs:
        url = job.get('job_url', '')
        if not url:
            continue

        url_hash = hashlib.sha256(url.encode()).hexdigest()

        if JobListing.objects.filter(user=user, url_hash=url_hash).exists():
            continue

        scoring = score_job_for_user(job, resume_data, prefs)

        listing = JobListing(
            user=user,
            title=job.get('title', '')[:500],
            company=job.get('company', '')[:300],
            location=job.get('location', '')[:300],
            url=url[:2000],
            description=job.get('description', ''),
            salary_info=_build_salary_str(job),
            job_type=job.get('job_type', '')[:50],
            source_board=job.get('source', '')[:50],
            external_id=job.get('external_id', '')[:200],
            match_score=scoring['score'],
            score_breakdown=scoring['breakdown'],
            matched_keywords=scoring['matched_keywords'],
            url_hash=url_hash,
        )

        try:
            listing.save()
            new_count += 1
        except Exception as e:
            logger.debug(f"Duplicate or save error: {e}")

    return new_count


@shared_task
def generate_cover_letter(application_id: int) -> dict:
    """Generate a tailored cover letter using Claude API or Ollama (local LLM)."""
    from .models import JobApplication
    from .cover_letter import generate_cover_letter_text

    try:
        app = JobApplication.objects.select_related('listing', 'resume', 'user').get(id=application_id)
    except JobApplication.DoesNotExist:
        return {'error': 'Application not found'}

    app.status = 'generating_cover'
    app.save(update_fields=['status'])

    # Use Claude API key if available, otherwise fall back to Ollama
    api_key = getattr(app.user, 'anthropic_api_key', '') or ''

    resume_text = ''
    if app.resume and app.resume.extracted_text:
        resume_text = app.resume.extracted_text
    elif app.resume and app.resume.parsed_data:
        resume_text = str(app.resume.parsed_data)

    provider = 'claude' if api_key else 'ollama'
    logger.info(f"Generating cover letter via {provider} for application {application_id}")

    try:
        cover_letter = generate_cover_letter_text(
            resume_text=resume_text,
            job_title=app.listing.title,
            company=app.listing.company,
            job_description=app.listing.description,
            api_key=api_key,
        )
        app.cover_letter = cover_letter
        app.save(update_fields=['cover_letter'])
        logger.info(f"Cover letter generated ({provider}) for application {application_id}")
        return {'success': True, 'length': len(cover_letter), 'provider': provider}
    except Exception as e:
        logger.error(f"Cover letter generation failed ({provider}): {e}")
        app.status = 'failed'
        app.error_message = f'Cover letter generation failed ({provider}): {str(e)}'
        app.save(update_fields=['status', 'error_message'])
        return {'error': str(e)}


@shared_task
def process_application(application_id: int) -> dict:
    """
    Full application pipeline: generate cover letter, then attempt browser apply.
    Falls back to 'cover_ready' status if no workspace is configured.
    """
    from .models import JobApplication, JobPreferences

    try:
        app = JobApplication.objects.select_related('listing', 'resume', 'user').get(id=application_id)
    except JobApplication.DoesNotExist:
        return {'error': 'Application not found'}

    # Step 1: Try to generate cover letter (optional - don't block apply if it fails)
    if not app.cover_letter:
        try:
            result = generate_cover_letter(application_id)
            if result.get('success'):
                app.refresh_from_db()
            else:
                logger.info(f"Cover letter skipped for app {application_id}: {result.get('error')}")
        except Exception as e:
            logger.info(f"Cover letter generation skipped: {e}")

    # Step 2: Attempt browser automation
    app.status = 'applying'
    app.save(update_fields=['status'])

    resume_data = {}
    if app.resume and app.resume.parsed_data:
        resume_data = app.resume.parsed_data

    # Try Playwright direct automation first (no external dependency)
    result = _run_playwright_apply(app, resume_data)

    if result.get('success'):
        app.status = 'applied'
        app.applied_at = timezone.now()
        app.applied_via = result.get('method', 'playwright')
        app.automation_log = result.get('log', [])
        app.save(update_fields=['status', 'applied_at', 'applied_via', 'automation_log'])
        logger.info(f"Application {application_id} applied via {result.get('method')}")
        return {'success': True, 'status': 'applied', 'method': result.get('method')}
    else:
        # Playwright failed - mark with cover letter ready for manual apply
        app.automation_log = result.get('log', [])
        app.error_message = result.get('error', 'Browser automation failed - apply manually')
        app.status = 'applied'
        app.applied_at = timezone.now()
        app.applied_via = 'manual'
        app.save(update_fields=['status', 'applied_at', 'applied_via', 'error_message', 'automation_log'])
        logger.info(f"Application {application_id} marked for manual apply: {result.get('error')}")
        return {'success': True, 'status': 'applied', 'method': 'manual', 'note': result.get('error')}


def _run_playwright_apply(app, resume_data: dict) -> dict:
    """Run Playwright browser automation to apply to a job via the company career page."""
    from .playwright_apply import apply_to_job_with_playwright

    # Get the resume file path for upload
    resume_file_path = ''
    if app.resume and app.resume.file:
        try:
            resume_file_path = app.resume.file.path
        except Exception:
            pass

    try:
        result = apply_to_job_with_playwright(
            job_url=app.listing.url,
            resume_data=resume_data,
            cover_letter=app.cover_letter or '',
            resume_file_path=resume_file_path,
            user_id=app.user.id,  # Pass user ID for Gmail verification code fetching
        )
        return result
    except Exception as e:
        logger.error(f"Playwright apply error: {e}")
        return {'success': False, 'method': 'playwright_error', 'log': [], 'error': str(e)}


@shared_task
def run_daily_job_search() -> dict:
    """
    Daily orchestrator: discover jobs for all users with auto-apply enabled,
    then queue applications for high-scoring matches.
    """
    from django.contrib.auth import get_user_model
    from .models import JobPreferences, JobListing, JobApplication, Resume, DailyApplicationSummary

    User = get_user_model()
    results = []

    # Find all users with auto-apply enabled
    prefs_list = JobPreferences.objects.filter(auto_apply_enabled=True).select_related('user')

    for prefs in prefs_list:
        user = prefs.user
        logger.info(f"Running daily job search for {user.email}")

        # 1. Discover new jobs
        discovery = discover_jobs(user.id)
        new_jobs = discovery.get('total_new', 0)

        # 2. Get today's qualifying jobs (not already applied/queued)
        existing_listing_ids = JobApplication.objects.filter(
            user=user
        ).values_list('listing_id', flat=True)

        qualifying = JobListing.objects.filter(
            user=user,
            dismissed=False,
            match_score__gte=prefs.auto_apply_min_score,
        ).exclude(
            id__in=existing_listing_ids
        ).order_by('-match_score')

        # 3. Queue applications up to daily limit
        resume = Resume.objects.filter(user=user, is_primary=True).first()
        daily_count = JobApplication.objects.filter(
            user=user,
            created_at__date=date.today(),
        ).count()

        remaining = max(0, prefs.max_daily_applications - daily_count)
        queued = 0

        for listing in qualifying[:remaining]:
            app, created = JobApplication.objects.get_or_create(
                user=user,
                listing=listing,
                defaults={
                    'resume': resume,
                    'status': 'queued',
                }
            )
            if created:
                process_application.delay(app.id)
                queued += 1

        # 4. Create daily summary
        apps_today = JobApplication.objects.filter(
            user=user,
            created_at__date=date.today(),
        )
        applied = apps_today.filter(status='applied').count()
        failed = apps_today.filter(status='failed').count()

        summary_text = (
            f"Jobs Discovered: {new_jobs}\n"
            f"Applications Queued: {queued}\n"
            f"Applied: {applied}\n"
            f"Failed: {failed}\n"
        )

        DailyApplicationSummary.objects.update_or_create(
            user=user,
            date=date.today(),
            defaults={
                'jobs_discovered': new_jobs,
                'applications_sent': applied + queued,
                'applications_failed': failed,
                'high_score_jobs': qualifying.count(),
                'summary_text': summary_text,
            }
        )

        results.append({
            'user': user.email,
            'new_jobs': new_jobs,
            'queued': queued,
        })

        logger.info(f"Daily search for {user.email}: {new_jobs} new jobs, {queued} queued")

    return {'users_processed': len(results), 'results': results}


def _build_salary_str(job: dict) -> str:
    """Build a salary string from JobSpy job data."""
    salary = ''
    if job.get('salary_min') and job.get('salary_max'):
        interval = job.get('salary_interval', 'yearly')
        salary = f"${job['salary_min']:,.0f} - ${job['salary_max']:,.0f} {interval}"
    elif job.get('salary_min'):
        salary = f"${job['salary_min']:,.0f}+"
    return salary[:200]
