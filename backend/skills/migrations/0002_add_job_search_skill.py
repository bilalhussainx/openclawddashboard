# Generated data migration for job-search-mcp skill

from django.db import migrations


def create_job_search_skill(apps, schema_editor):
    """Create the job-search-mcp skill in the database."""
    Skill = apps.get_model('skills', 'Skill')

    skill_content = """# Job Search MCP Skill

Search for jobs across LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google Jobs using JobSpy.

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Indeed | ✅ Best | Most reliable, good for large searches |
| LinkedIn | ✅ Works | Rate limited, use sparingly |
| Glassdoor | ✅ Works | Includes salary data and reviews |
| ZipRecruiter | ✅ Works | US/Canada jobs |
| Google Jobs | ✅ Works | Aggregated listings |

## Usage Examples

### Basic Search
```python
from jobspy import scrape_jobs

jobs = scrape_jobs(
    site_name=['indeed', 'linkedin'],
    search_term='python developer',
    location='remote',
    results_wanted=10
)
```

### With Filters
```python
jobs = scrape_jobs(
    site_name=['indeed'],
    search_term='software engineer',
    location='San Francisco, CA',
    results_wanted=20,
    hours_old=24,           # Posted in last 24 hours
    job_type='fulltime',    # fulltime, parttime, contract, internship
    is_remote=True,
    country_indeed='usa'
)
```

### Available Fields in Results
- `title` - Job title
- `company` - Company name
- `location` - Job location
- `job_url` - Direct link to posting
- `min_amount` / `max_amount` - Salary range
- `job_type` - Employment type
- `date_posted` - When posted
- `description` - Full job description

## Rate Limits & Best Practices

1. **Start small** - Begin with 10-15 results
2. **Use Indeed first** - Most reliable source
3. **LinkedIn sparingly** - Has strict rate limits
4. **Add delays** - Wait between searches
5. **Be specific** - Use targeted search terms

## No API Key Required

This skill uses JobSpy which scrapes job boards directly. No API keys or login required.
"""

    Skill.objects.update_or_create(
        slug='job-search-mcp',
        defaults={
            'name': 'Job Search',
            'description': 'Search for jobs across LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google Jobs. Uses JobSpy to scrape job listings without requiring API keys or login. Supports filtering by location, job type, salary, and posting date.',
            'short_description': 'Search jobs on LinkedIn, Indeed, Glassdoor & more',
            'author': 'ClawHub',
            'author_url': 'https://clawhub.com',
            'repository_url': 'https://github.com/Bunsly/JobSpy',
            'category': 'automation',
            'tags': ['jobs', 'linkedin', 'indeed', 'career', 'scraping', 'automation'],
            'clawhub_id': 'job-search-mcp',
            'version': '1.0.0',
            'is_official': True,
            'is_featured': True,
            'is_active': True,
            'skill_content': skill_content,
            'required_tools': ['python', 'jobspy'],
            'required_env': [],  # No API keys required!
        }
    )

    # Also add the job-auto-apply skill
    job_auto_apply_content = """# Job Auto-Apply Skill

Automated job search AND application system. Not only finds jobs but can also apply to them automatically.

## Features

- **Multi-Platform Search** - LinkedIn, Indeed, Glassdoor, ZipRecruiter, Wellfound
- **Smart Matching** - Analyzes job compatibility with your profile
- **Auto Cover Letters** - Generates tailored cover letters per job
- **Form Automation** - Fills application forms automatically
- **LinkedIn Easy Apply** - Supports one-click applications
- **Application Tracking** - Logs all submissions

## Setup

1. Create your profile with resume, skills, and preferences
2. Define search criteria (title, location, salary range)
3. Run in dry-run mode first to test
4. Enable auto-apply when ready

## Usage

```bash
# Dry run - search without applying
python job_search_apply.py --title "Software Engineer" --location "Remote" --dry-run

# With auto-apply
python job_search_apply.py --profile ~/job_profile.json --title "Backend Engineer" --auto-apply
```

## Safety Features

- Dry Run Mode - Test without submitting
- Manual Confirmation - Review before sending
- Rate Limiting - Respects platform limits
- Application Logging - Tracks all submissions
"""

    Skill.objects.update_or_create(
        slug='job-auto-apply',
        defaults={
            'name': 'Job Auto-Apply',
            'description': 'Automated job search and application system. Searches for jobs matching your criteria, generates tailored cover letters, fills application forms, and submits applications automatically with tracking.',
            'short_description': 'Search and auto-apply to jobs across platforms',
            'author': 'ClawHub',
            'author_url': 'https://clawhub.com',
            'category': 'automation',
            'tags': ['jobs', 'linkedin', 'indeed', 'automation', 'career', 'applications'],
            'clawhub_id': 'job-auto-apply',
            'version': '1.0.0',
            'is_official': True,
            'is_featured': True,
            'is_active': True,
            'skill_content': job_auto_apply_content,
            'required_tools': ['python', 'jobspy', 'browser'],
            'required_env': [],
        }
    )

    # Add DuckDuckGo search skill
    Skill.objects.update_or_create(
        slug='duckduckgo-search',
        defaults={
            'name': 'DuckDuckGo Search',
            'description': 'Privacy-friendly web search using DuckDuckGo. Search for text, news, images, and videos without tracking. No API key required.',
            'short_description': 'Free web search without API keys',
            'author': 'ClawHub',
            'author_url': 'https://clawhub.com',
            'category': 'productivity',
            'tags': ['search', 'web', 'duckduckgo', 'privacy'],
            'clawhub_id': 'duckduckgo-search',
            'version': '1.0.0',
            'is_official': True,
            'is_featured': False,
            'is_active': True,
            'skill_content': '# DuckDuckGo Search\n\nFree web search using DuckDuckGo.\n\n```python\nfrom duckduckgo_search import DDGS\n\nwith DDGS() as ddgs:\n    results = list(ddgs.text("your query", max_results=5))\n```',
            'required_tools': ['python', 'duckduckgo-search'],
            'required_env': [],
        }
    )


def remove_job_search_skill(apps, schema_editor):
    """Remove the job search skills."""
    Skill = apps.get_model('skills', 'Skill')
    Skill.objects.filter(slug__in=['job-search-mcp', 'job-auto-apply', 'duckduckgo-search']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_job_search_skill, remove_job_search_skill),
    ]
