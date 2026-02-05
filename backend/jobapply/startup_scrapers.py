"""
Startup/AI job board scrapers: Hacker News "Who's Hiring" and RemoteOK.
Each function returns: {success: bool, jobs: list[dict], total: int, errors: list[str]}
Job dicts match the JobSpy format: {title, company, location, job_url, description, source, ...}
"""
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
REQUEST_TIMEOUT = 20

# Module-level caches to avoid re-fetching within the same discovery run
_hn_cache = {'thread_id': None, 'comments': [], 'fetched_at': None}
_remoteok_cache = {'jobs': [], 'fetched_at': None}


def _empty_result(errors=None):
    return {'success': False, 'jobs': [], 'total': 0, 'errors': errors or []}


def _success_result(jobs):
    return {'success': True, 'jobs': jobs, 'total': len(jobs), 'errors': []}


# ---------------------------------------------------------------------------
# Hacker News "Who's Hiring"
# ---------------------------------------------------------------------------

def _fetch_hn_comment(cid):
    """Fetch a single HN comment by ID from Firebase API."""
    try:
        url = f"https://hacker-news.firebaseio.com/v0/item/{cid}.json"
        resp = requests.get(url, timeout=10)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return None


def _parse_salary(text: str) -> tuple:
    """Extract salary min/max from text like '$120k-$180k' or '$120,000 - $180,000'."""
    match = re.search(
        r'\$(\d{2,3}),?(\d{3})?\s*[kK]?\s*[-\u2013to]+\s*\$(\d{2,3}),?(\d{3})?\s*[kK]?',
        text
    )
    if match:
        min_str = match.group(1) + (match.group(2) or '')
        max_str = match.group(3) + (match.group(4) or '')
        min_val = int(min_str)
        max_val = int(max_str)
        if min_val < 1000:
            min_val *= 1000
        if max_val < 1000:
            max_val *= 1000
        return min_val, max_val
    return None, None


def _parse_hn_comment(comment: dict) -> Optional[dict]:
    """
    Parse a single HN 'Who is Hiring' comment into structured job data.

    Common format (pipe-delimited first line):
      Company Name | City, State (Remote) | Role Title | $Xk-$Yk | https://...
    """
    html = comment.get('text', '')
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)

    if len(text) < 20:
        return None

    lines = text.split('\n')
    first_line = lines[0]
    parts = [p.strip() for p in first_line.split('|')]

    company = ''
    location = ''
    title = ''
    salary = ''
    job_url = ''

    if len(parts) >= 2:
        company = parts[0]
        for part in parts[1:]:
            # URL
            url_match = re.search(r'https?://\S+', part)
            if url_match:
                job_url = url_match.group(0).rstrip(')')
                continue
            # Salary
            salary_match = re.search(r'\$[\d,]+[kK]?\s*[-\u2013]\s*\$[\d,]+[kK]?', part)
            if salary_match:
                salary = salary_match.group(0)
                continue
            # Location hints
            if re.search(r'(remote|onsite|hybrid|NYC|SF|Toronto|Canada|USA|EU|Berlin|London)', part, re.I):
                location = part
                continue
            if re.search(r'\b[A-Z]{2}\b', part) and len(part) < 40:
                location = part
                continue
            # Default: title
            if not title:
                title = part
    else:
        company = first_line[:100]

    # Extract URL from anywhere in text
    if not job_url:
        all_urls = re.findall(r'https?://\S+', text)
        if all_urls:
            job_url = all_urls[0].rstrip(')')

    # Clean URL out of company name
    url_in_company = re.search(r'\(?\s*https?://\S+\s*\)?', company)
    if url_in_company:
        if not job_url:
            job_url = re.search(r'https?://\S+', url_in_company.group(0)).group(0).rstrip(')')
        company = re.sub(r'\s*\(?\s*https?://\S+\s*\)?\s*', '', company).strip()

    description = '\n'.join(lines[1:]).strip()
    salary_min, salary_max = _parse_salary(salary or text)
    comment_id = comment.get('id', '')

    if not company or not (title or description):
        return None

    return {
        'title': (title or 'See Description')[:500],
        'company': company[:300],
        'location': location[:300],
        'job_url': job_url or f'https://news.ycombinator.com/item?id={comment_id}',
        'description': description[:2000],
        'source': 'hn_hiring',
        'salary_min': salary_min,
        'salary_max': salary_max,
        'salary_interval': 'yearly' if salary_min else '',
        'job_type': '',
        'external_id': str(comment_id),
    }


def scrape_hn_hiring(
    search_term: str,
    max_results: int = 30,
    location_filter: str = '',
    remote_ok: bool = True,
) -> dict:
    """
    Scrape Hacker News monthly 'Who is Hiring' thread.
    Uses Algolia search API + HN Firebase API. Both free, no auth.
    """
    global _hn_cache

    try:
        # Check cache (reuse within 10 min)
        now = datetime.now()
        if (_hn_cache['comments']
                and _hn_cache['fetched_at']
                and (now - _hn_cache['fetched_at']).seconds < 600):
            comments = _hn_cache['comments']
            logger.info(f"HN: using cached {len(comments)} comments")
        else:
            # Find latest "Who is hiring" thread via Algolia
            algolia_url = "https://hn.algolia.com/api/v1/search"
            params = {
                'query': '"Ask HN: Who is hiring"',
                'tags': 'story',
                'hitsPerPage': 5,
            }
            resp = requests.get(algolia_url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            hits = sorted(
                data.get('hits', []),
                key=lambda h: h.get('created_at_i', 0),
                reverse=True,
            )
            if not hits:
                return _empty_result(['No HN Who is Hiring thread found'])

            thread_id = hits[0]['objectID']
            logger.info(f"HN: found thread {thread_id}: {hits[0].get('title', '')}")

            # Fetch thread to get comment IDs
            hn_url = f"https://hacker-news.firebaseio.com/v0/item/{thread_id}.json"
            thread = requests.get(hn_url, timeout=REQUEST_TIMEOUT).json()
            comment_ids = thread.get('kids', [])

            if not comment_ids:
                return _empty_result(['HN thread has no comments'])

            # Fetch comments in parallel (cap at 200)
            comments = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(_fetch_hn_comment, cid): cid
                    for cid in comment_ids[:200]
                }
                for future in as_completed(futures):
                    comment = future.result()
                    if comment and not comment.get('deleted') and not comment.get('dead'):
                        comments.append(comment)

            _hn_cache = {'thread_id': thread_id, 'comments': comments, 'fetched_at': now}
            logger.info(f"HN: fetched {len(comments)} comments")

        # Parse comments into jobs
        parsed = []
        for comment in comments:
            job = _parse_hn_comment(comment)
            if job:
                parsed.append(job)

        # Filter by search term
        search_terms = [t.lower() for t in search_term.lower().split() if len(t) > 2]
        filtered = []
        for job in parsed:
            combined = f"{job['title']} {job['company']} {job['description']}".lower()
            if any(term in combined for term in search_terms):
                filtered.append(job)
            if len(filtered) >= max_results:
                break

        # Also filter by location if specified
        if location_filter:
            loc = location_filter.lower()
            location_filtered = []
            for job in filtered:
                job_loc = job['location'].lower()
                job_desc = job['description'].lower()
                if (loc in job_loc or loc in job_desc
                        or 'remote' in job_loc
                        or (remote_ok and 'remote' in job_desc)):
                    location_filtered.append(job)
            filtered = location_filtered

        logger.info(f"HN: {len(parsed)} parsed, {len(filtered)} matched '{search_term}'")
        return _success_result(filtered)

    except Exception as e:
        logger.error(f"HN scraper failed: {e}")
        return _empty_result([str(e)])


# ---------------------------------------------------------------------------
# RemoteOK
# ---------------------------------------------------------------------------

def _clean_html(html_text: str) -> str:
    """Strip HTML tags from text."""
    if not html_text:
        return ''
    soup = BeautifulSoup(html_text, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


def _parse_remoteok_salary(val) -> Optional[float]:
    """Parse RemoteOK salary value."""
    if val is None:
        return None
    try:
        return float(str(val).replace(',', '').replace('$', ''))
    except (ValueError, TypeError):
        return None


def scrape_remoteok(
    search_term: str,
    max_results: int = 30,
) -> dict:
    """
    Fetch jobs from RemoteOK JSON API and filter by search term.
    API: GET https://remoteok.io/api (no auth, returns full JSON dump)
    """
    global _remoteok_cache

    try:
        now = datetime.now()
        if (_remoteok_cache['jobs']
                and _remoteok_cache['fetched_at']
                and (now - _remoteok_cache['fetched_at']).seconds < 600):
            raw_jobs = _remoteok_cache['jobs']
            logger.info(f"RemoteOK: using cached {len(raw_jobs)} jobs")
        else:
            response = requests.get(
                'https://remoteok.io/api',
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            # First item is metadata/legal notice, skip it
            raw_jobs = data[1:] if len(data) > 1 else []
            _remoteok_cache = {'jobs': raw_jobs, 'fetched_at': now}
            logger.info(f"RemoteOK: fetched {len(raw_jobs)} jobs")

        search_terms = [t.lower() for t in search_term.lower().split() if len(t) > 2]
        jobs = []

        for raw in raw_jobs:
            tags = raw.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]

            searchable = ' '.join([
                raw.get('position', ''),
                raw.get('company', ''),
                ' '.join(tags),
                raw.get('description', '')[:500],
            ]).lower()

            if not any(term in searchable for term in search_terms):
                continue

            job = {
                'title': raw.get('position', '')[:500],
                'company': raw.get('company', '')[:300],
                'location': (raw.get('location', '') or 'Remote')[:300],
                'job_url': (
                    raw.get('apply_url', '')
                    or raw.get('url', '')
                    or f"https://remoteok.io/remote-jobs/{raw.get('id', '')}"
                ),
                'description': _clean_html(raw.get('description', ''))[:2000],
                'source': 'remoteok',
                'salary_min': _parse_remoteok_salary(raw.get('salary_min')),
                'salary_max': _parse_remoteok_salary(raw.get('salary_max')),
                'salary_interval': 'yearly' if raw.get('salary_min') else '',
                'job_type': 'fulltime',
                'external_id': str(raw.get('id', '')),
            }
            jobs.append(job)

            if len(jobs) >= max_results:
                break

        logger.info(f"RemoteOK: {len(jobs)} matched '{search_term}'")
        return _success_result(jobs)

    except Exception as e:
        logger.error(f"RemoteOK scraper failed: {e}")
        return _empty_result([str(e)])


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

STARTUP_BOARD_NAMES = {'hn_hiring', 'remoteok'}


def scrape_startup_boards(
    search_term: str,
    enabled_boards: list,
    location: str = '',
    remote_ok: bool = True,
    max_results_per_board: int = 15,
) -> dict:
    """
    Orchestrate scraping across enabled startup/AI boards.
    Returns combined result in same format as scrape_jobs_with_jobspy().
    """
    all_jobs = []
    all_errors = []

    scrapers = {
        'hn_hiring': lambda: scrape_hn_hiring(
            search_term=search_term,
            max_results=max_results_per_board,
            location_filter=location,
            remote_ok=remote_ok,
        ),
        'remoteok': lambda: scrape_remoteok(
            search_term=search_term,
            max_results=max_results_per_board,
        ),
    }

    for board in enabled_boards:
        if board not in scrapers:
            continue

        logger.info(f"Scraping {board} for '{search_term}'")
        try:
            result = scrapers[board]()
            if result.get('success'):
                all_jobs.extend(result.get('jobs', []))
            if result.get('errors'):
                all_errors.extend([f"{board}: {e}" for e in result['errors']])
        except Exception as e:
            logger.error(f"Scraper {board} crashed: {e}")
            all_errors.append(f"{board}: {str(e)}")

    return {
        'success': len(all_jobs) > 0 or len(all_errors) == 0,
        'jobs': all_jobs,
        'total': len(all_jobs),
        'errors': all_errors,
    }
