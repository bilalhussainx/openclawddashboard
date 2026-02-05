"""
ClawHub Sync Service - Fetches and syncs skills from the official ClawHub registry.

ClawHub is the official skill marketplace for OpenClaw with 3000+ community-built skills.
Registry: https://www.clawhub.ai/skills
GitHub: https://github.com/openclaw/clawhub
"""
import logging
import requests
import json
import re
from typing import List, Dict, Any, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)

# ClawHub API endpoints
CLAWHUB_API_BASE = "https://api.clawhub.ai"
CLAWHUB_REGISTRY = "https://www.clawhub.ai"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Awesome OpenClaw Skills - curated list of 1700+ skills
AWESOME_SKILLS_URL = "https://raw.githubusercontent.com/VoltAgent/awesome-openclaw-skills/main/README.md"

# Categories mapping from ClawHub to our model
CATEGORY_MAPPING = {
    'devops': 'development',
    'cloud': 'development',
    'ai': 'data',
    'llm': 'data',
    'search': 'productivity',
    'research': 'productivity',
    'coding': 'development',
    'ide': 'development',
    'web': 'development',
    'frontend': 'development',
    'communication': 'communication',
    'messaging': 'communication',
    'social': 'communication',
    'automation': 'automation',
    'workflow': 'automation',
    'database': 'data',
    'analytics': 'data',
    'productivity': 'productivity',
    'calendar': 'productivity',
    'notes': 'productivity',
    'finance': 'data',
    'security': 'development',
    'fun': 'fun',
    'entertainment': 'fun',
    'games': 'fun',
}

# Featured/Popular skills to highlight
FEATURED_SKILLS = [
    'web-search',
    'browser',
    'github',
    'filesystem',
    'memory',
    'sequential-thinking',
    'postgres',
    'sqlite',
    'docker',
    'kubernetes',
    'slack',
    'discord',
    'notion',
    'google-drive',
    'google-calendar',
    'aws',
    'azure',
    'puppeteer',
    'playwright',
    'exa',
    'brave-search',
    'perplexity',
    'firecrawl',
    'e2b',
]


def fetch_clawhub_skills(limit: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch skills from the ClawHub API.

    Returns list of skill metadata dictionaries.
    """
    skills = []

    try:
        # Try the ClawHub API first
        response = requests.get(
            f"{CLAWHUB_API_BASE}/v1/skills",
            params={'limit': limit, 'sort': 'popular'},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            skills = data.get('skills', data.get('results', []))
            logger.info(f"Fetched {len(skills)} skills from ClawHub API")
            return skills

    except Exception as e:
        logger.warning(f"ClawHub API unavailable: {e}, falling back to GitHub")

    # Fallback: Parse the Awesome OpenClaw Skills list
    skills = parse_awesome_skills_list()

    return skills


def parse_awesome_skills_list() -> List[Dict[str, Any]]:
    """
    Parse the Awesome OpenClaw Skills curated list from GitHub.
    This list contains 1700+ categorized and vetted skills.
    """
    skills = []

    try:
        response = requests.get(AWESOME_SKILLS_URL, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to fetch awesome skills list: {response.status_code}")
            return get_default_skills()

        content = response.text

        # Parse markdown to extract skills
        current_category = 'other'

        for line in content.split('\n'):
            line = line.strip()

            # Detect category headers
            if line.startswith('## ') or line.startswith('### '):
                category_name = line.lstrip('#').strip().lower()
                for key, mapped in CATEGORY_MAPPING.items():
                    if key in category_name:
                        current_category = mapped
                        break
                continue

            # Parse skill entries (format: - [Name](url) - description)
            skill_match = re.match(
                r'-\s*\[([^\]]+)\]\(([^)]+)\)\s*[-–:]\s*(.+)',
                line
            )

            if skill_match:
                name = skill_match.group(1).strip()
                url = skill_match.group(2).strip()
                description = skill_match.group(3).strip()

                # Generate slug from name
                slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

                # Extract author from GitHub URL
                author = 'Community'
                if 'github.com' in url:
                    parts = url.split('github.com/')
                    if len(parts) > 1:
                        author = parts[1].split('/')[0]

                skills.append({
                    'name': name,
                    'slug': slug,
                    'description': description,
                    'short_description': description[:200] if len(description) > 200 else description,
                    'author': author,
                    'repository_url': url if 'github.com' in url else '',
                    'category': current_category,
                    'clawhub_id': slug,
                    'tags': extract_tags(name, description),
                    'is_official': author.lower() in ['anthropic', 'modelcontextprotocol', 'openclaw'],
                })

        logger.info(f"Parsed {len(skills)} skills from Awesome list")

    except Exception as e:
        logger.error(f"Failed to parse awesome skills: {e}")
        return get_default_skills()

    return skills if skills else get_default_skills()


def extract_tags(name: str, description: str) -> List[str]:
    """Extract relevant tags from skill name and description."""
    tags = []
    text = f"{name} {description}".lower()

    # Common technology tags
    tech_keywords = [
        'api', 'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'postgres', 'mysql', 'mongodb', 'redis', 'sqlite',
        'python', 'javascript', 'typescript', 'node', 'react',
        'github', 'gitlab', 'git', 'ci/cd', 'devops',
        'slack', 'discord', 'telegram', 'email',
        'calendar', 'drive', 'notion', 'confluence',
        'ai', 'llm', 'ml', 'embedding', 'vector',
        'search', 'browser', 'scraping', 'crawl',
        'memory', 'rag', 'knowledge', 'database',
    ]

    for keyword in tech_keywords:
        if keyword in text:
            tags.append(keyword)

    return tags[:10]  # Limit to 10 tags


def get_default_skills() -> List[Dict[str, Any]]:
    """
    Return a curated list of essential skills when API/GitHub fails.
    These are the most popular and useful skills for OpenClaw agents.
    """
    return [
        # Search & Web
        {
            'name': 'Web Search',
            'slug': 'web-search',
            'description': 'Search the web using various search engines (Google, Bing, DuckDuckGo). Essential for agents that need current information.',
            'short_description': 'Search the web for current information',
            'author': 'OpenClaw',
            'category': 'productivity',
            'clawhub_id': 'web-search',
            'tags': ['search', 'web', 'google', 'bing'],
            'is_official': True,
            'required_env': ['GOOGLE_API_KEY', 'GOOGLE_CSE_ID'],
        },
        {
            'name': 'Brave Search',
            'slug': 'brave-search',
            'description': 'Privacy-focused web search using Brave Search API. No tracking, fast results.',
            'short_description': 'Privacy-focused web search via Brave',
            'author': 'OpenClaw',
            'category': 'productivity',
            'clawhub_id': 'brave-search',
            'tags': ['search', 'web', 'brave', 'privacy'],
            'is_official': True,
            'required_env': ['BRAVE_API_KEY'],
        },
        {
            'name': 'Exa Search',
            'slug': 'exa',
            'description': 'Neural search engine with embeddings-based search. Better semantic understanding than keyword search.',
            'short_description': 'Neural search with semantic understanding',
            'author': 'Exa',
            'category': 'productivity',
            'clawhub_id': 'exa',
            'tags': ['search', 'ai', 'embeddings', 'semantic'],
            'required_env': ['EXA_API_KEY'],
        },

        # Browser & Scraping
        {
            'name': 'Playwright Browser',
            'slug': 'playwright',
            'description': 'Control a real browser to navigate web pages, fill forms, click buttons, and extract content. Handles JavaScript-heavy sites.',
            'short_description': 'Browser automation and web scraping',
            'author': 'Microsoft',
            'category': 'automation',
            'clawhub_id': 'playwright',
            'tags': ['browser', 'automation', 'scraping', 'web'],
            'is_official': True,
        },
        {
            'name': 'Puppeteer',
            'slug': 'puppeteer',
            'description': 'Headless Chrome browser automation. Navigate pages, take screenshots, generate PDFs.',
            'short_description': 'Chrome automation and scraping',
            'author': 'Google',
            'category': 'automation',
            'clawhub_id': 'puppeteer',
            'tags': ['browser', 'chrome', 'automation', 'scraping'],
        },
        {
            'name': 'Firecrawl',
            'slug': 'firecrawl',
            'description': 'Turn any website into clean, LLM-ready data. Handles JavaScript rendering, bypasses bot detection.',
            'short_description': 'Convert websites to LLM-ready data',
            'author': 'Firecrawl',
            'category': 'automation',
            'clawhub_id': 'firecrawl',
            'tags': ['scraping', 'crawl', 'web', 'llm'],
            'required_env': ['FIRECRAWL_API_KEY'],
        },

        # Code & Development
        {
            'name': 'GitHub',
            'slug': 'github',
            'description': 'Full GitHub integration - create repos, manage issues, pull requests, actions, and more.',
            'short_description': 'Full GitHub API integration',
            'author': 'GitHub',
            'category': 'development',
            'clawhub_id': 'github',
            'tags': ['github', 'git', 'code', 'repos'],
            'is_official': True,
            'required_env': ['GITHUB_TOKEN'],
        },
        {
            'name': 'Filesystem',
            'slug': 'filesystem',
            'description': 'Read, write, and manage files and directories. Essential for file-based tasks.',
            'short_description': 'File and directory operations',
            'author': 'OpenClaw',
            'category': 'development',
            'clawhub_id': 'filesystem',
            'tags': ['files', 'filesystem', 'io'],
            'is_official': True,
        },
        {
            'name': 'Docker',
            'slug': 'docker',
            'description': 'Manage Docker containers, images, networks, and volumes. Run isolated environments.',
            'short_description': 'Docker container management',
            'author': 'Docker',
            'category': 'development',
            'clawhub_id': 'docker',
            'tags': ['docker', 'containers', 'devops'],
        },
        {
            'name': 'Kubernetes',
            'slug': 'kubernetes',
            'description': 'Execute and manage Kubernetes clusters via kubectl. Deploy, scale, and monitor pods.',
            'short_description': 'Kubernetes cluster management',
            'author': 'Community',
            'category': 'development',
            'clawhub_id': 'kubernetes',
            'tags': ['kubernetes', 'k8s', 'containers', 'devops'],
        },

        # Databases
        {
            'name': 'PostgreSQL',
            'slug': 'postgres',
            'description': 'Connect to PostgreSQL databases. Run queries, manage schemas, analyze data.',
            'short_description': 'PostgreSQL database operations',
            'author': 'OpenClaw',
            'category': 'data',
            'clawhub_id': 'postgres',
            'tags': ['database', 'postgres', 'sql'],
            'is_official': True,
            'required_env': ['POSTGRES_CONNECTION_STRING'],
        },
        {
            'name': 'SQLite',
            'slug': 'sqlite',
            'description': 'Work with SQLite databases. Perfect for local data storage and analysis.',
            'short_description': 'SQLite database operations',
            'author': 'OpenClaw',
            'category': 'data',
            'clawhub_id': 'sqlite',
            'tags': ['database', 'sqlite', 'sql'],
            'is_official': True,
        },

        # Memory & Knowledge
        {
            'name': 'Memory',
            'slug': 'memory',
            'description': 'Long-term memory for your agent using vector databases. Remember context across conversations.',
            'short_description': 'Persistent memory across conversations',
            'author': 'OpenClaw',
            'category': 'data',
            'clawhub_id': 'memory',
            'tags': ['memory', 'vector', 'embeddings', 'rag'],
            'is_official': True,
        },
        {
            'name': 'Sequential Thinking',
            'slug': 'sequential-thinking',
            'description': 'Break down complex problems into steps. Better reasoning for multi-step tasks.',
            'short_description': 'Step-by-step reasoning for complex tasks',
            'author': 'OpenClaw',
            'category': 'productivity',
            'clawhub_id': 'sequential-thinking',
            'tags': ['reasoning', 'thinking', 'planning'],
            'is_official': True,
        },

        # Communication
        {
            'name': 'Slack',
            'slug': 'slack',
            'description': 'Send messages, manage channels, and interact with Slack workspaces.',
            'short_description': 'Slack workspace integration',
            'author': 'Slack',
            'category': 'communication',
            'clawhub_id': 'slack',
            'tags': ['slack', 'messaging', 'chat'],
            'required_env': ['SLACK_BOT_TOKEN'],
        },
        {
            'name': 'Discord',
            'slug': 'discord',
            'description': 'Send messages and manage Discord servers and channels.',
            'short_description': 'Discord server integration',
            'author': 'Discord',
            'category': 'communication',
            'clawhub_id': 'discord',
            'tags': ['discord', 'messaging', 'chat'],
            'required_env': ['DISCORD_BOT_TOKEN'],
        },
        {
            'name': 'Email',
            'slug': 'email',
            'description': 'Send and read emails via SMTP/IMAP. Supports Gmail, Outlook, and custom servers.',
            'short_description': 'Email sending and reading',
            'author': 'Community',
            'category': 'communication',
            'clawhub_id': 'email',
            'tags': ['email', 'smtp', 'gmail'],
            'required_env': ['EMAIL_ADDRESS', 'EMAIL_PASSWORD'],
        },

        # Productivity
        {
            'name': 'Google Calendar',
            'slug': 'google-calendar',
            'description': 'Manage Google Calendar events - create, update, delete, and query calendar events.',
            'short_description': 'Google Calendar management',
            'author': 'Google',
            'category': 'productivity',
            'clawhub_id': 'google-calendar',
            'tags': ['calendar', 'google', 'scheduling'],
            'required_env': ['GOOGLE_CREDENTIALS'],
        },
        {
            'name': 'Google Drive',
            'slug': 'google-drive',
            'description': 'Access and manage files in Google Drive. Upload, download, search, and share.',
            'short_description': 'Google Drive file management',
            'author': 'Google',
            'category': 'productivity',
            'clawhub_id': 'google-drive',
            'tags': ['drive', 'google', 'files', 'storage'],
            'required_env': ['GOOGLE_CREDENTIALS'],
        },
        {
            'name': 'Notion',
            'slug': 'notion',
            'description': 'Read and write Notion pages and databases. Perfect for knowledge management.',
            'short_description': 'Notion pages and databases',
            'author': 'Notion',
            'category': 'productivity',
            'clawhub_id': 'notion',
            'tags': ['notion', 'notes', 'database', 'wiki'],
            'required_env': ['NOTION_API_KEY'],
        },

        # Cloud
        {
            'name': 'AWS',
            'slug': 'aws',
            'description': 'Interact with AWS services - S3, EC2, Lambda, and more via the AWS CLI.',
            'short_description': 'Amazon Web Services integration',
            'author': 'Amazon',
            'category': 'development',
            'clawhub_id': 'aws',
            'tags': ['aws', 'cloud', 's3', 'lambda'],
            'required_env': ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'],
        },
        {
            'name': 'E2B',
            'slug': 'e2b',
            'description': 'Run code in secure cloud sandboxes. Execute Python, Node, and shell safely.',
            'short_description': 'Secure cloud code execution',
            'author': 'E2B',
            'category': 'development',
            'clawhub_id': 'e2b',
            'tags': ['sandbox', 'code', 'execution', 'cloud'],
            'required_env': ['E2B_API_KEY'],
        },

        # Job Search (Custom)
        {
            'name': 'Job Search',
            'slug': 'job-search-mcp',
            'description': 'Search for jobs across LinkedIn, Indeed, Glassdoor, ZipRecruiter using JobSpy. Free, no API keys required.',
            'short_description': 'Search jobs on LinkedIn, Indeed & more',
            'author': 'ClawHub',
            'category': 'automation',
            'clawhub_id': 'job-search-mcp',
            'tags': ['jobs', 'linkedin', 'indeed', 'career'],
            'is_official': True,
        },
        {
            'name': 'DuckDuckGo Search',
            'slug': 'duckduckgo-search',
            'description': 'Privacy-friendly web search using DuckDuckGo. No API key required.',
            'short_description': 'Free web search, no API key needed',
            'author': 'ClawHub',
            'category': 'productivity',
            'clawhub_id': 'duckduckgo-search',
            'tags': ['search', 'web', 'duckduckgo', 'privacy', 'free'],
            'is_official': True,
        },
    ]


def sync_skills_to_database(skills: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Sync fetched skills to the database.
    Creates new skills and updates existing ones.

    Returns dict with counts: {'created': X, 'updated': Y, 'errors': Z}
    """
    from .models import Skill

    stats = {'created': 0, 'updated': 0, 'errors': 0}

    for skill_data in skills:
        try:
            slug = skill_data.get('slug') or skill_data.get('clawhub_id', '')
            if not slug:
                continue

            # Check if featured
            is_featured = slug in FEATURED_SKILLS or skill_data.get('is_official', False)

            # Map category
            category = skill_data.get('category', 'other')
            if category not in [c[0] for c in Skill.Category.choices]:
                category = 'other'

            defaults = {
                'name': skill_data.get('name', slug),
                'description': skill_data.get('description', ''),
                'short_description': skill_data.get('short_description', '')[:200],
                'author': skill_data.get('author', 'Community'),
                'author_url': skill_data.get('author_url', ''),
                'repository_url': skill_data.get('repository_url', ''),
                'category': category,
                'tags': skill_data.get('tags', []),
                'clawhub_id': skill_data.get('clawhub_id', slug),
                'version': skill_data.get('version', '1.0.0'),
                'is_official': skill_data.get('is_official', False),
                'is_featured': is_featured,
                'is_active': True,
                'skill_content': skill_data.get('skill_content', ''),
                'required_tools': skill_data.get('required_tools', []),
                'required_env': skill_data.get('required_env', []),
            }

            skill, created = Skill.objects.update_or_create(
                slug=slug,
                defaults=defaults
            )

            if created:
                stats['created'] += 1
            else:
                stats['updated'] += 1

        except Exception as e:
            logger.error(f"Failed to sync skill {skill_data.get('slug')}: {e}")
            stats['errors'] += 1

    logger.info(f"Skill sync complete: {stats}")
    return stats


def sync_clawhub_skills():
    """
    Main sync function - fetches skills from ClawHub and syncs to database.
    Call this periodically via Celery beat or management command.
    """
    logger.info("Starting ClawHub skill sync...")

    # Fetch skills
    skills = fetch_clawhub_skills(limit=500)

    if not skills:
        logger.warning("No skills fetched, using defaults")
        skills = get_default_skills()

    # Sync to database
    stats = sync_skills_to_database(skills)

    logger.info(f"ClawHub sync complete: {stats['created']} created, {stats['updated']} updated")

    return stats


def get_skill_install_command(skill_slug: str) -> str:
    """
    Get the clawhub install command for a skill.
    """
    return f"npx clawhub install {skill_slug}"


def get_skill_content(skill_slug: str) -> Optional[str]:
    """
    Fetch the SKILL.md content for a skill from ClawHub.
    """
    try:
        # Try ClawHub API first
        response = requests.get(
            f"{CLAWHUB_API_BASE}/v1/skills/{skill_slug}/content",
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('content', '')
    except Exception:
        pass

    # Fallback: try GitHub raw
    common_repos = [
        f"openclaw/skills/{skill_slug}",
        f"modelcontextprotocol/servers/src/{skill_slug}",
    ]

    for repo in common_repos:
        try:
            url = f"{GITHUB_RAW_BASE}/{repo}/main/SKILL.md"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception:
            continue

    return None
