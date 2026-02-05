"""
Agent Task execution - Uses AI to accomplish user-defined tasks.
"""
import json
import logging
import requests
import time
import asyncio
import re
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================================
# OpenClaw Gateway Client - Connect to workspace container for browser control
# ============================================================================

class OpenClawGatewayClient:
    """
    WebSocket client for OpenClaw Gateway.
    Allows Celery tasks to use browser skills installed in the workspace container.
    """

    PROTOCOL_VERSION = 3  # OpenClaw Gateway protocol version

    def __init__(self, gateway_url: str, token: str = None):
        self.gateway_url = gateway_url
        self.token = token
        self.ws = None
        self.request_id = 0

    async def connect(self):
        """Connect to OpenClaw Gateway using the official protocol."""
        try:
            import websockets
            import uuid

            self.ws = await websockets.connect(self.gateway_url, ping_timeout=60, max_size=25*1024*1024)
            logger.info(f"Connected to OpenClaw Gateway: {self.gateway_url}")

            # Wait for connect.challenge event
            challenge_msg = await asyncio.wait_for(self.ws.recv(), timeout=10)
            challenge = json.loads(challenge_msg)

            if challenge.get('event') == 'connect.challenge':
                nonce = challenge['payload'].get('nonce')
                logger.info(f"Received challenge, nonce: {nonce[:20] if nonce else 'none'}...")

                # Build connect request per OpenClaw protocol v3
                connect_params = {
                    "minProtocol": self.PROTOCOL_VERSION,
                    "maxProtocol": self.PROTOCOL_VERSION,
                    "client": {
                        "id": "gateway-client",  # Must be a valid client ID
                        "displayName": "Celery Job Search",
                        "version": "1.0.0",
                        "platform": "linux",
                        "mode": "backend",
                    },
                    "caps": [],
                    "role": "operator",
                    "scopes": ["operator.admin"],
                }

                # Add auth if token provided
                if self.token:
                    connect_params["auth"] = {"token": self.token}

                # Send connect request (type must be "req" per OpenClaw protocol)
                request = {
                    "type": "req",
                    "id": str(uuid.uuid4()),
                    "method": "connect",
                    "params": connect_params,
                }
                await self.ws.send(json.dumps(request))
                logger.info("Sent connect request")

                # Wait for response
                response_msg = await asyncio.wait_for(self.ws.recv(), timeout=15)
                response = json.loads(response_msg)

                if response.get('ok') is True:
                    logger.info("Gateway authentication successful!")
                    return True
                elif response.get('error'):
                    error = response.get('error', {})
                    logger.error(f"Gateway auth failed: {error.get('message', error)}")
                    return False
                else:
                    logger.info(f"Got response: {str(response)[:200]}")
                    return True  # Assume connected if no error

            return True
        except Exception as e:
            logger.error(f"Failed to connect to OpenClaw Gateway: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def disconnect(self):
        """Disconnect from Gateway."""
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def send_request(self, method: str, params: dict = None, timeout: int = 30):
        """Send request to Gateway using OpenClaw protocol.

        Waits for the response matching our request ID, filtering out event messages.
        """
        import uuid

        if not self.ws:
            return None

        self.request_id += 1
        request_id = str(uuid.uuid4())
        request = {
            "type": "req",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        await self.ws.send(json.dumps(request))

        # Wait for response with matching ID, skip events
        start_time = asyncio.get_event_loop().time()
        while True:
            try:
                remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                if remaining <= 0:
                    logger.warning(f"Request {method} timed out")
                    return None

                response = await asyncio.wait_for(self.ws.recv(), timeout=remaining)
                msg = json.loads(response)

                # Check if this is our response
                if msg.get("type") == "res" and msg.get("id") == request_id:
                    return msg

                # Log and skip event messages
                if msg.get("type") == "event":
                    event_name = msg.get("event", "unknown")
                    logger.debug(f"Received event while waiting for response: {event_name}")
                    continue

                # Other message types - log but continue waiting
                logger.debug(f"Received non-matching message: {msg.get('type')}")

            except asyncio.TimeoutError:
                logger.warning(f"Request {method} timed out waiting for response")
                return None

    async def send_agent_request(self, message: str, timeout_seconds: int = 180) -> dict:
        """
        Send a message to the agent and collect all streaming events until completion.

        Returns dict with:
        - success: bool
        - text: str (full response text)
        - events: list (all events received)
        - error: str (if failed)
        """
        import uuid

        if not self.ws:
            return {"success": False, "error": "Not connected", "text": "", "events": []}

        session_key = f"celery-{uuid.uuid4().hex[:12]}"
        idempotency_key = str(uuid.uuid4())

        # Send agent request
        request = {
            "type": "req",
            "id": str(uuid.uuid4()),
            "method": "agent",
            "params": {
                "message": message,
                "idempotencyKey": idempotency_key,
                "sessionId": session_key,
                "timeout": timeout_seconds,
            }
        }

        logger.info(f"Sending agent request: {message[:50]}...")
        await self.ws.send(json.dumps(request))

        # Collect events and responses
        events = []
        full_text = ""
        run_id = None
        error = None

        try:
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout_seconds:
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=30)
                    data = json.loads(msg)
                    events.append(data)

                    msg_type = data.get('type')

                    if msg_type == 'event':
                        event_name = data.get('event')

                        if event_name == 'agent':
                            payload = data.get('payload', {})
                            event_type = payload.get('event')

                            # Collect text from streaming events
                            if event_type == 'text':
                                text = payload.get('text', '')
                                full_text += text

                            elif event_type == 'tool_use':
                                tool_name = payload.get('toolName', '')
                                logger.info(f"Agent using tool: {tool_name}")

                            elif event_type == 'tool_result':
                                logger.info("Agent received tool result")

                            elif event_type == 'done':
                                logger.info("Agent completed")
                                return {
                                    "success": True,
                                    "text": full_text,
                                    "events": events,
                                    "error": None
                                }

                            elif event_type == 'error':
                                error = payload.get('message', 'Unknown error')
                                logger.error(f"Agent error: {error}")
                                return {
                                    "success": False,
                                    "text": full_text,
                                    "events": events,
                                    "error": error
                                }

                    elif msg_type == 'res':
                        # Initial response with runId
                        if data.get('ok'):
                            payload = data.get('payload', {})
                            run_id = payload.get('runId')
                            status = payload.get('status')
                            logger.info(f"Agent request accepted: runId={run_id}, status={status}")
                            # Continue waiting for events
                        else:
                            error = data.get('error', {}).get('message', 'Request failed')
                            logger.error(f"Agent request failed: {error}")
                            return {
                                "success": False,
                                "text": "",
                                "events": events,
                                "error": error
                            }

                except asyncio.TimeoutError:
                    # Continue waiting unless we've exceeded total timeout
                    continue

        except Exception as e:
            logger.error(f"Error collecting agent events: {e}")
            return {
                "success": False,
                "text": full_text,
                "events": events,
                "error": str(e)
            }

        # Timeout reached
        logger.warning(f"Agent request timed out after {timeout_seconds}s")
        return {
            "success": len(full_text) > 0,
            "text": full_text,
            "events": events,
            "error": "Timeout" if not full_text else None
        }

    async def browser_navigate(self, url: str, wait_ms: int = 3000):
        """Navigate browser to URL."""
        result = await self.send_request("browser.navigate", {
            "url": url,
            "waitUntil": "networkidle",
            "timeout": 20000
        })
        await asyncio.sleep(wait_ms / 1000)
        return result

    async def browser_get_content(self):
        """Get page text content."""
        result = await self.send_request("browser.snapshot", {
            "type": "text"
        })
        if result and "result" in result:
            return result["result"].get("text", "")
        return ""

    async def browser_get_links(self):
        """Get all links from current page."""
        result = await self.send_request("browser.evaluate", {
            "expression": "Array.from(document.querySelectorAll('a[href]')).map(a => a.href).filter(h => h)"
        })
        if result and "result" in result:
            return result["result"]
        return []

    async def browser_request(self, method: str, path: str, query: dict = None, body: dict = None):
        """
        Send a browser control request using the browser.request Gateway method.
        This is the direct browser API that bypasses the agent.
        """
        params = {"method": method, "path": path, "query": query or {}}
        if body:
            params["body"] = body
        return await self.send_request("browser.request", params)

    async def browser_start(self, profile: str = "openclaw"):
        """Start the browser with specified profile."""
        return await self.browser_request("POST", "/start", {"profile": profile})

    async def browser_stop(self, profile: str = "openclaw"):
        """Stop the browser."""
        return await self.browser_request("POST", "/stop", {"profile": profile})

    async def browser_navigate_direct(self, url: str, profile: str = "openclaw"):
        """Navigate browser directly to a URL."""
        return await self.browser_request("POST", "/navigate", {"profile": profile}, {"url": url})

    async def browser_snapshot(self, profile: str = "openclaw"):
        """Get accessibility tree snapshot of current page."""
        return await self.browser_request("GET", "/snapshot", {"profile": profile})

    async def browser_click(self, ref: str, profile: str = "openclaw"):
        """Click an element by its ref from snapshot."""
        return await self.browser_request("POST", "/act", {"profile": profile}, {
            "action": "click",
            "ref": ref
        })

    async def browser_type(self, ref: str, text: str, profile: str = "openclaw"):
        """Type text into an element."""
        return await self.browser_request("POST", "/act", {"profile": profile}, {
            "action": "type",
            "ref": ref,
            "text": text
        })


async def scrape_jobs_with_browser(gateway: OpenClawGatewayClient, url: str, profile: str = "openclaw") -> dict:
    """
    Scrape job listings from a URL using direct browser control.
    Returns parsed job data from the page snapshot.
    """
    result = {"success": False, "jobs": [], "error": None, "raw_snapshot": ""}

    try:
        # First stop any existing browser to avoid port conflicts
        try:
            await gateway.browser_stop(profile)
            await asyncio.sleep(1)
        except Exception:
            pass  # Ignore stop errors

        # Start browser
        start_result = await gateway.browser_start(profile)
        if not start_result or not start_result.get("ok"):
            error = start_result.get("error", {}).get("message", "Failed to start browser") if start_result else "No response"
            # If port in use, try to force reset by waiting
            if error and "in use" in error.lower():
                logger.warning("Port in use, waiting and retrying...")
                await asyncio.sleep(3)
                start_result = await gateway.browser_start(profile)
                if not start_result or not start_result.get("ok"):
                    result["error"] = error
                    return result
            else:
                result["error"] = error
                logger.error(f"Browser start failed: {error}")
                return result

        logger.info("Browser started successfully")

        # Navigate to URL
        await asyncio.sleep(1)
        nav_result = await gateway.browser_navigate_direct(url, profile)
        if not nav_result or not nav_result.get("ok"):
            error = nav_result.get("error", {}).get("message", "Navigation failed") if nav_result else "No response"
            result["error"] = error
            logger.error(f"Navigation failed: {error}")
            return result

        logger.info(f"Navigated to {url}")

        # Wait for page to load
        await asyncio.sleep(3)

        # Get snapshot
        snap_result = await gateway.browser_snapshot(profile)
        if not snap_result or not snap_result.get("ok"):
            error = snap_result.get("error", {}).get("message", "Snapshot failed") if snap_result else "No response"
            result["error"] = error
            logger.error(f"Snapshot failed: {error}")
            return result

        payload = snap_result.get("payload", {})
        snapshot = payload.get("snapshot", "")
        result["raw_snapshot"] = snapshot
        result["url"] = payload.get("url", url)

        logger.info(f"Got snapshot: {len(snapshot)} chars")

        # Parse jobs from snapshot
        jobs = parse_jobs_from_snapshot(snapshot, url)
        result["jobs"] = jobs
        result["success"] = True

        logger.info(f"Parsed {len(jobs)} jobs from snapshot")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Browser scraping error: {e}")

    finally:
        # Stop browser
        try:
            await gateway.browser_stop(profile)
            logger.info("Browser stopped")
        except Exception as e:
            logger.warning(f"Failed to stop browser: {e}")

    return result


def parse_jobs_from_snapshot(snapshot: str, source_url: str) -> list:
    """
    Parse job listings from an accessibility tree snapshot.
    Works with common job board formats.
    """
    jobs = []
    lines = snapshot.split("\n")

    # Track current job being parsed
    current_job = None

    for i, line in enumerate(lines):
        line = line.strip()

        # Look for job-related patterns
        # RemoteOK pattern: row with job title, company, salary
        if 'row "' in line and ('Engineer' in line or 'Developer' in line or 'Software' in line or 'job' in line.lower()):
            # Extract job info from row
            job = {"source": source_url}

            # Extract title - usually in heading or link
            if 'heading "' in line:
                title_match = re.search(r'heading "([^"]+)"', line)
                if title_match:
                    job["title"] = title_match.group(1)

            # Extract salary
            if '$' in line:
                salary_match = re.search(r'\$[\d,]+k?\s*-?\s*\$?[\d,]*k?', line)
                if salary_match:
                    job["salary"] = salary_match.group(0)

            # Extract company
            if '🎈' in line:
                # Company often follows balloon emoji
                parts = line.split('🎈')
                if len(parts) > 1:
                    company_part = parts[1].split('🇪')[0].split('🌎')[0].split('💰')[0].strip()
                    job["company"] = company_part

            if job.get("title"):
                jobs.append(job)
                current_job = job

        # Look for links with job URLs
        elif '/url:' in line and current_job:
            url_match = re.search(r'/url:\s*(\S+)', line)
            if url_match:
                job_url = url_match.group(1)
                if '/remote-jobs/' in job_url or '/job/' in job_url:
                    current_job["url"] = job_url
                    if not job_url.startswith('http'):
                        # Make relative URL absolute
                        from urllib.parse import urljoin
                        current_job["url"] = urljoin(source_url, job_url)

        # Extract job title from heading
        elif 'heading "' in line and ('Engineer' in line or 'Developer' in line):
            title_match = re.search(r'heading "([^"]+)"', line)
            if title_match:
                title = title_match.group(1)
                if current_job and not current_job.get("title"):
                    current_job["title"] = title
                elif title not in [j.get("title") for j in jobs]:
                    jobs.append({"title": title, "source": source_url})

        # Extract links
        elif 'link "' in line and '/url:' in lines[i+1] if i+1 < len(lines) else False:
            link_match = re.search(r'link "([^"]+)"', line)
            if link_match and current_job:
                link_text = link_match.group(1)
                if not current_job.get("title") and ('Engineer' in link_text or 'Developer' in link_text):
                    current_job["title"] = link_text

    return jobs


def get_workspace_gateway_info(workspace):
    """Get the Gateway WebSocket URL and token for a workspace container."""
    from workspaces.models import Workspace as WS
    import docker

    if not workspace.container_id or workspace.status != WS.Status.RUNNING:
        return None, None

    port = workspace.assigned_port
    if not port:
        return None, None

    # Get token from workspace
    token = getattr(workspace, 'gateway_token', None)

    # Get container IP address (containers may be on different networks)
    try:
        client = docker.from_env()
        container = client.containers.get(workspace.container_id)

        # Try to get IP from any network
        networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
        for net_name, net_info in networks.items():
            ip = net_info.get('IPAddress')
            if ip:
                logger.info(f"Found container IP: {ip} on network {net_name}")
                return f"ws://{ip}:{port}", token

        # Fallback to container name
        logger.warning("Could not get container IP, using hostname")
        return f"ws://openclaw-workspace-{workspace.id}:{port}", token

    except Exception as e:
        logger.error(f"Failed to get container IP: {e}")
        return None, None


def get_workspace_gateway_url(workspace):
    """Get the Gateway WebSocket URL for a workspace container (backwards compat)."""
    url, _ = get_workspace_gateway_info(workspace)
    return url


async def search_jobs_via_gateway(gateway: OpenClawGatewayClient, search_terms: list,
                                   job_sites: list, location: str = None) -> list:
    """
    Search for jobs using OpenClaw Gateway agent with async event handling.

    Sends a message to the agent to search for jobs using its installed skills
    (like Web Search, Playwright Browser, etc.) and collects streaming results.
    """
    # Build a search prompt for the agent
    terms_str = ", ".join(search_terms[:4])
    sites_str = ", ".join(job_sites[:5])
    location_str = location if location else "remote"

    prompt = f"""Search for job openings that require skills in: {terms_str}

Use web search to find jobs on: {sites_str}
Location preference: {location_str}

Search queries to use:
- "{search_terms[0]}" jobs site:linkedin.com
- "{search_terms[0]}" hiring site:indeed.com
- "{search_terms[0]}" remote jobs

For each job found, provide in this EXACT format (one per line):
JOB: [Title] | COMPANY: [Company] | URL: [Full URL] | DESC: [Brief description]

Find at least 10 relevant job postings. Only include jobs that specifically mention {search_terms[0]} or related AI/coding tools.
"""

    logger.info(f"Sending job search request to Gateway agent...")

    # Use the async agent method that handles event streaming
    result = await gateway.send_agent_request(prompt, timeout_seconds=180)

    if not result.get('success'):
        logger.error(f"Agent search failed: {result.get('error')}")
        return []

    # Parse the agent's response text to extract job listings
    job_results = []
    response_text = result.get('text', '')
    logger.info(f"Agent returned {len(response_text)} chars of text")

    # Parse structured job listings from the response
    for line in response_text.split('\n'):
        line = line.strip()
        if line.startswith('JOB:') or '| COMPANY:' in line or '| URL:' in line:
            # Parse the structured format
            job_data = {'title': '', 'company': '', 'url': '', 'content': line}

            # Extract URL
            if '| URL:' in line:
                url_part = line.split('| URL:')[1].split('|')[0].strip()
                job_data['url'] = url_part

            # Extract title
            if line.startswith('JOB:'):
                title_part = line.split('JOB:')[1].split('|')[0].strip()
                job_data['title'] = title_part
            elif '|' in line:
                job_data['title'] = line.split('|')[0].strip()

            # Extract company
            if '| COMPANY:' in line:
                company_part = line.split('| COMPANY:')[1].split('|')[0].strip()
                job_data['company'] = company_part

            if job_data.get('url') and ('http' in job_data['url']):
                job_results.append(job_data)
                logger.info(f"  Found job: {job_data['title'][:40]}... at {job_data['url'][:50]}")

    # Also try to extract any URLs from the full response
    import re
    url_pattern = r'https?://[^\s<>"\']+(?:linkedin\.com/jobs|indeed\.com|lever\.co|greenhouse\.io)[^\s<>"\']*'
    found_urls = set(job['url'] for job in job_results)
    for url in re.findall(url_pattern, response_text):
        if url not in found_urls and is_job_url(url):
            job_results.append({'url': url, 'title': '', 'company': '', 'content': ''})
            found_urls.add(url)
            logger.info(f"  Extracted URL: {url[:60]}...")

    logger.info(f"Parsed {len(job_results)} job results from agent response")
    return job_results


async def scrape_job_pages_via_gateway(gateway: OpenClawGatewayClient, job_urls: list,
                                        max_jobs: int = 15) -> list:
    """Scrape individual job pages using Gateway agent with async event handling."""
    scraped_jobs = []

    for i, job_data in enumerate(job_urls[:max_jobs]):
        url = job_data.get('url', '')
        if not url:
            continue

        logger.info(f"Scraping job {i+1}/{min(len(job_urls), max_jobs)}: {url[:50]}...")

        try:
            # Use agent to scrape the page content
            prompt = f"""Navigate to this job posting and extract the full content:
{url}

Provide:
1. Job title
2. Company name
3. Location
4. Full job description
5. Requirements and qualifications
6. Any mentioned technologies or tools

Format the response clearly."""

            result = await gateway.send_agent_request(prompt, timeout_seconds=60)

            if result.get('success') and result.get('text'):
                job_data['content'] = result['text'][:4000]
                scraped_jobs.append(job_data)
                logger.info(f"  Got {len(result['text'])} chars from agent")
            else:
                logger.warning(f"  Agent returned no content: {result.get('error')}")

            await asyncio.sleep(1)  # Rate limit

        except Exception as e:
            logger.error(f"  Scrape failed: {e}")

    return scraped_jobs


def run_gateway_job_search(workspace, search_terms: list, location: str = None) -> list:
    """
    Run job search via OpenClaw Gateway (synchronous wrapper).
    Returns list of scraped job data.
    """
    gateway_url, gateway_token = get_workspace_gateway_info(workspace)
    if not gateway_url:
        logger.error("Workspace not running or no gateway URL")
        return []

    logger.info(f"Gateway URL: {gateway_url}, Token: {'present' if gateway_token else 'missing'}")

    async def _search():
        gateway = OpenClawGatewayClient(gateway_url, gateway_token)

        if not await gateway.connect():
            logger.error("Failed to connect to Gateway")
            return []

        try:
            # Search for jobs
            job_urls = await search_jobs_via_gateway(
                gateway, search_terms, JOB_SITES, location
            )
            logger.info(f"Found {len(job_urls)} job URLs via Gateway")

            if not job_urls:
                return []

            # Scrape job pages
            scraped = await scrape_job_pages_via_gateway(gateway, job_urls, max_jobs=15)
            logger.info(f"Scraped {len(scraped)} job pages")

            return scraped

        finally:
            await gateway.disconnect()

    # Run async function
    return asyncio.run(_search())

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    'min_delay_between_calls': 1.0,  # Minimum seconds between API calls
    'max_retries': 3,                # Max retries on rate limit
    'base_backoff': 2.0,             # Base backoff in seconds
    'max_backoff': 60.0,             # Max backoff in seconds
}

# Token/complexity limits
COMPLEXITY_LIMITS = {
    'max_tool_result_chars': 4000,   # Truncate tool results to this length
    'max_iterations': 25,            # Max agent iterations (increased for complex tasks)
    'max_tokens_response': 4096,     # Max tokens for AI response (increased for detailed outputs)
    'max_input_tokens_estimate': 150000,  # Token budget for complex tasks like travel planning
}

# Track last API call time per user to enforce rate limits
_last_api_call = {}

# Job board sites to search (like the standalone script)
JOB_SITES = [
    "linkedin.com/jobs",
    "indeed.com",
    "lever.co",
    "greenhouse.io",
    "jobs.ashbyhq.com",
    "wellfound.com",
    "workatastartup.com",
    "remoteok.com",
    "weworkremotely.com",
    "builtin.com/jobs",
]

# Default AI tool search terms
DEFAULT_AI_SEARCH_TERMS = [
    "Claude Code",
    "Cursor",
    "GitHub Copilot",
    "AI-assisted developer",
    "Vibe Coding",
    "AI-Native",
]

# Keywords for scoring jobs based on AI tools usage
AI_TOOLS_SCORE_KEYWORDS = {
    # High score (30 pts each) - Explicit AI coding tools
    'claude code': 30,
    'claude-code': 30,
    'cursor ide': 30,
    'cursor ai': 30,
    'github copilot': 30,
    'copilot': 25,
    'codeium': 25,
    'tabnine': 20,
    'ai pair programming': 30,
    'ai-assisted coding': 30,
    'vibe coding': 30,

    # Medium score (15 pts each) - AI/LLM related
    'ai-native': 20,
    'ai native': 20,
    'llm': 15,
    'large language model': 15,
    'prompt engineering': 15,
    'ai tools': 15,
    'ai assistant': 15,
    'generative ai': 15,
    'anthropic': 20,
    'openai': 15,
    'gpt-4': 15,
    'claude': 20,

    # Lower score (10 pts each) - Modern dev practices
    'developer experience': 10,
    'developer tools': 10,
    'devtools': 10,
    'productivity tools': 10,
    'automation': 10,
    'python': 5,
    'typescript': 5,
    'remote': 10,
    'startup': 10,
}


def calculate_job_score(job: dict) -> tuple:
    """
    Calculate a match score for a job based on AI tools keywords.

    Returns (score, matched_keywords) where:
    - score: 0-100 based on keyword matches
    - matched_keywords: list of keywords that matched

    Scoring:
    - 90-100: Perfect match - explicitly mentions AI coding tools
    - 70-89: Strong match - AI/LLM related
    - 50-69: Moderate match - Modern dev practices
    - 0-49: Low match - Generic job
    """
    text_to_search = ' '.join([
        str(job.get('title', '')),
        str(job.get('company', '')),
        str(job.get('description', '')),
        str(job.get('location', '')),
    ]).lower()

    total_score = 0
    matched = []

    for keyword, points in AI_TOOLS_SCORE_KEYWORDS.items():
        if keyword in text_to_search:
            total_score += points
            matched.append(keyword)

    # Cap at 100
    final_score = min(100, total_score)

    return final_score, matched

# Tool definitions that the agent can use
# Base tools that are always available
BASE_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for information. Use this to find websites, articles, job postings, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (max 10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "scrape_webpage",
        "description": "Scrape content from a webpage URL. Returns the text content of the page. For JavaScript-heavy sites like LinkedIn/Indeed, use firecrawl_scrape instead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to scrape"
                },
                "extract": {
                    "type": "string",
                    "description": "What to extract: 'text', 'links', 'structured'",
                    "default": "text"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "firecrawl_scrape",
        "description": "Scrape JavaScript-rendered pages using Firecrawl. Perfect for LinkedIn, Indeed, Glassdoor, and other job boards that block simple scrapers. Returns clean markdown content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to scrape (works with LinkedIn, Indeed, Glassdoor, etc.)"
                },
                "formats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Output formats: 'markdown', 'html', 'links'",
                    "default": ["markdown"]
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "firecrawl_search",
        "description": "Search the web using Firecrawl and get scraped content from results. Great for finding and extracting job listings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'software engineer jobs LinkedIn')"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to scrape (max 10)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_jobs",
        "description": "Search for job postings on job boards. Uses free APIs (RemoteOK, Remotive) by default. For LinkedIn/Indeed, use firecrawl_scrape or serper_jobs instead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Job search query (title, keywords)"
                },
                "location": {
                    "type": "string",
                    "description": "Location (city, state, or 'remote')"
                },
                "site": {
                    "type": "string",
                    "description": "Which site to search: 'linkedin', 'indeed', 'remoteok', 'all'",
                    "default": "all"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "serper_jobs",
        "description": "Search for jobs using Serper API (Google Jobs). Returns job listings from Google's job search including LinkedIn, Indeed, Glassdoor results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Job search query (e.g., 'software engineer')"
                },
                "location": {
                    "type": "string",
                    "description": "Location (e.g., 'New York', 'Remote')",
                    "default": ""
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (max 20)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "send_message",
        "description": "Send a message to the user via their connected channel (Telegram, Slack, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to send"
                },
                "format": {
                    "type": "string",
                    "description": "Message format: 'text', 'markdown'",
                    "default": "markdown"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "save_result",
        "description": "Save a structured result (job, article, product, etc.) for the user to review later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "Result type: 'job', 'article', 'product', etc."
                },
                "title": {
                    "type": "string",
                    "description": "Title of the result"
                },
                "url": {
                    "type": "string",
                    "description": "URL link"
                },
                "score": {
                    "type": "number",
                    "description": "Your score/rating (0-100)"
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary"
                },
                "data": {
                    "type": "object",
                    "description": "Additional structured data"
                }
            },
            "required": ["type", "title"]
        }
    }
]


def get_tools_for_workspace(workspace):
    """
    Get available tools for a workspace, including installed skills.
    Returns tools list and skill instructions for the system prompt.
    """
    tools = list(BASE_TOOLS)  # Start with base tools
    skill_instructions = ""

    # Add tools from installed skills
    installed_skills = workspace.installed_skills.filter(
        is_enabled=True,
        install_status='ready'
    ).select_related('skill')

    for installed in installed_skills:
        skill = installed.skill

        # Add skill instructions to system prompt
        skill_instructions += f"\n### {skill.name}\n"
        skill_instructions += f"{skill.description}\n"
        if skill.skill_content:
            skill_instructions += f"\n{skill.skill_content}\n"

    return tools, skill_instructions


def is_job_search_task(instructions: str) -> bool:
    """Detect if task is a job search (route to efficient pipeline)."""
    job_keywords = [
        'job', 'jobs', 'career', 'hiring', 'position', 'opening',
        'linkedin', 'indeed', 'glassdoor', 'remote work',
        'software engineer', 'developer', 'full-stack', 'backend', 'frontend',
        'job posting', 'job listing', 'employment'
    ]
    instructions_lower = instructions.lower()
    return any(kw in instructions_lower for kw in job_keywords)


@shared_task
def execute_agent_task(task_id):
    """
    Execute an agent task using AI to interpret instructions and use tools.
    Routes job searches to efficient pipeline, other tasks to agentic loop.
    """
    from .models import AgentTask, TaskRun, TaskResult

    try:
        task = AgentTask.objects.select_related('workspace', 'workspace__owner').get(id=task_id)
    except AgentTask.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return

    # Route job searches to the efficient pipeline
    if is_job_search_task(task.instructions):
        logger.info(f"Task {task_id} detected as job search - using pipeline")
        return execute_job_search_pipeline(task_id)

    workspace = task.workspace
    user = workspace.owner

    # Get API key
    api_key = user.anthropic_api_key or user.openai_api_key
    use_anthropic = bool(user.anthropic_api_key)

    if not api_key:
        task.last_error = "No API key configured"
        task.save()
        return

    # Create run record
    run = TaskRun.objects.create(
        task=task,
        status='running'
    )

    task.status = AgentTask.Status.RUNNING
    task.save()

    try:
        # Get tools and skill instructions for this workspace
        available_tools, skill_instructions = get_tools_for_workspace(workspace)

        # Build concise system prompt to reduce tokens
        system_prompt = f"""Task: {task.instructions}

CRITICAL: You MUST call send_message to notify the user. Do NOT skip this step.

Workflow:
1. Do ONE search to find results
2. Call save_result for top 3-5 matches
3. IMMEDIATELY call send_message with a summary for the user

Keep it simple - one search is usually enough. Always end with send_message."""

        # Add installed skill instructions if any (truncated)
        if skill_instructions:
            # Truncate skill instructions to reduce token usage
            truncated_skills = skill_instructions[:2000] if len(skill_instructions) > 2000 else skill_instructions
            system_prompt += f"\n\nSkills available:\n{truncated_skills}"

        # Build the initial message
        messages = [
            {"role": "user", "content": task.instructions}
        ]

        steps_taken = []
        tools_used = []
        total_tokens = 0
        max_iterations = COMPLEXITY_LIMITS['max_iterations']

        # Cap max_tokens for responses to reduce complexity
        response_max_tokens = min(
            workspace.max_tokens or 1024,
            COMPLEXITY_LIMITS['max_tokens_response']
        )

        logger.info(f"Starting task {task_id} with max_iterations={max_iterations}, max_tokens={response_max_tokens}")

        for iteration in range(max_iterations):
            # Call the AI with rate limiting and retry
            if use_anthropic:
                response, tokens = call_with_retry(
                    call_anthropic,
                    user.id,
                    api_key=api_key,
                    model=workspace.selected_model,
                    system=system_prompt,
                    messages=messages,
                    tools=available_tools,
                    max_tokens=response_max_tokens,
                )
            else:
                response, tokens = call_with_retry(
                    call_openai,
                    user.id,
                    api_key=api_key,
                    model=workspace.selected_model,
                    system=system_prompt,
                    messages=messages,
                    tools=available_tools,
                    max_tokens=response_max_tokens,
                )

            total_tokens += tokens
            logger.info(f"Iteration {iteration + 1}: used {tokens} tokens, total: {total_tokens}")

            # Check token budget - stop early if using too many tokens
            token_budget = COMPLEXITY_LIMITS.get('max_input_tokens_estimate', 20000)
            if total_tokens > token_budget:
                logger.warning(f"Token budget exceeded ({total_tokens} > {token_budget}), stopping early")
                steps_taken.append({
                    'action': 'budget_exceeded',
                    'tokens_used': total_tokens,
                })
                break

            # Check if we need to use tools
            if response.get('stop_reason') == 'tool_use' or response.get('tool_calls'):
                tool_calls = response.get('tool_calls', [])

                # Process each tool call
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call['name']
                    tool_input = tool_call['input']

                    logger.info(f"Agent using tool: {tool_name}")
                    tools_used.append(tool_name)
                    steps_taken.append({
                        'action': 'tool_call',
                        'tool': tool_name,
                        'input': tool_input,
                    })

                    # Execute the tool
                    tool_result = execute_tool(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        task=task,
                        run=run,
                    )

                    # Truncate tool result to reduce token usage
                    truncated_result = truncate_result(tool_result)

                    tool_results.append({
                        'tool_use_id': tool_call.get('id'),
                        'content': truncated_result,
                    })

                # Add assistant message and tool results to conversation
                # For Anthropic: content already contains tool_use blocks, no separate tool_calls field
                messages.append({
                    "role": "assistant",
                    "content": response.get('content', []),
                })
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", **tr} for tr in tool_results],
                })

            else:
                # Agent is done (no more tool calls)
                final_response = response.get('text', '')
                steps_taken.append({
                    'action': 'complete',
                    'response': final_response[:500],  # Truncate for storage
                })
                break

        # FALLBACK: If send_message was never called, send a summary to user
        if 'send_message' not in tools_used:
            logger.info("Agent never called send_message, sending fallback notification")
            # Build a summary from saved results
            saved_results = TaskResult.objects.filter(task=task, run=run)
            if saved_results.exists():
                summary = f"Task completed. Found {saved_results.count()} results:\n\n"
                for r in saved_results[:5]:
                    summary += f"• {r.title}\n  {r.url}\n\n"
            else:
                summary = f"Task '{task.instructions[:100]}' completed but no results were saved. Tools used: {', '.join(tools_used[:5])}"

            # Send the fallback message
            fallback_result = do_send_message(workspace, summary, "markdown")
            logger.info(f"Fallback message result: {fallback_result}")
            tools_used.append('send_message (fallback)')

        # Update run record
        run.status = 'completed'
        run.completed_at = timezone.now()
        run.agent_reasoning = final_response if 'final_response' in dir() else ''
        run.tools_used = list(set(tools_used))
        run.steps_taken = steps_taken
        run.tokens_used = total_tokens
        run.save()

        # Update task
        task.status = AgentTask.Status.COMPLETED
        task.last_run = timezone.now()
        task.run_count += 1
        task.last_result = run.agent_reasoning[:1000]
        task.last_error = ''
        task.save()

        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")

        run.status = 'failed'
        run.completed_at = timezone.now()
        run.error_message = str(e)
        run.save()

        task.status = AgentTask.Status.FAILED
        task.last_error = str(e)
        task.save()


def truncate_result(result, max_chars=None):
    """Truncate tool results to reduce token usage."""
    if max_chars is None:
        max_chars = COMPLEXITY_LIMITS['max_tool_result_chars']

    if isinstance(result, str) and len(result) > max_chars:
        return result[:max_chars] + f"\n\n[... truncated, {len(result) - max_chars} chars omitted]"
    return result


def enforce_rate_limit(user_id):
    """Enforce minimum delay between API calls per user."""
    global _last_api_call

    now = time.time()
    last_call = _last_api_call.get(user_id, 0)
    min_delay = RATE_LIMIT_CONFIG['min_delay_between_calls']

    elapsed = now - last_call
    if elapsed < min_delay:
        sleep_time = min_delay - elapsed
        logger.info(f"Rate limiting: sleeping {sleep_time:.2f}s for user {user_id}")
        time.sleep(sleep_time)

    _last_api_call[user_id] = time.time()


def call_with_retry(func, user_id, *args, **kwargs):
    """Call an API function with exponential backoff on rate limit errors."""
    max_retries = RATE_LIMIT_CONFIG['max_retries']
    base_backoff = RATE_LIMIT_CONFIG['base_backoff']
    max_backoff = RATE_LIMIT_CONFIG['max_backoff']

    for attempt in range(max_retries + 1):
        try:
            enforce_rate_limit(user_id)
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = '429' in error_str or 'rate_limit' in error_str or 'rate limit' in error_str

            if is_rate_limit and attempt < max_retries:
                backoff = min(base_backoff * (2 ** attempt), max_backoff)
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries + 1}), backing off {backoff}s")
                time.sleep(backoff)
                continue
            raise


def call_anthropic(api_key, model, system, messages, tools, max_tokens):
    """Call Anthropic's Claude API with tools."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    # Convert tools to Anthropic format
    anthropic_tools = [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        }
        for tool in tools
    ]

    # Convert messages to Anthropic format
    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "user":
            if isinstance(msg["content"], list):
                anthropic_messages.append({"role": "user", "content": msg["content"]})
            else:
                anthropic_messages.append({
                    "role": "user",
                    "content": msg["content"]
                })
        elif msg["role"] == "assistant":
            # Convert content to proper format if needed
            content = msg.get("content", [])
            if isinstance(content, list):
                # Convert Block objects to dicts if needed
                formatted_content = []
                for block in content:
                    if hasattr(block, 'type'):
                        # It's an Anthropic Block object
                        if block.type == 'text':
                            formatted_content.append({"type": "text", "text": block.text})
                        elif block.type == 'tool_use':
                            formatted_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })
                    elif isinstance(block, dict):
                        formatted_content.append(block)
                anthropic_messages.append({"role": "assistant", "content": formatted_content})
            else:
                anthropic_messages.append({"role": "assistant", "content": content})

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=anthropic_messages,
        tools=anthropic_tools,
    )

    # Parse response - convert to serializable format
    content_list = []
    for block in response.content:
        if block.type == 'text':
            content_list.append({"type": "text", "text": block.text})
        elif block.type == 'tool_use':
            content_list.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })

    result = {
        "stop_reason": response.stop_reason,
        "content": content_list,
        "tool_calls": [],
        "text": "",
    }

    for block in response.content:
        if block.type == "text":
            result["text"] = block.text
        elif block.type == "tool_use":
            result["tool_calls"].append({
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })

    tokens = response.usage.input_tokens + response.usage.output_tokens
    return result, tokens


def call_openai(api_key, model, system, messages, tools, max_tokens):
    """Call OpenAI's API with tools."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    # Convert tools to OpenAI format
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            }
        }
        for tool in tools
    ]

    # Convert messages
    openai_messages = [{"role": "system", "content": system}]
    for msg in messages:
        if msg["role"] == "user":
            if isinstance(msg["content"], str):
                openai_messages.append({"role": "user", "content": msg["content"]})
            # Handle tool results
        elif msg["role"] == "assistant":
            openai_messages.append(msg)

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=openai_messages,
        tools=openai_tools if openai_tools else None,
    )

    choice = response.choices[0]
    result = {
        "stop_reason": choice.finish_reason,
        "content": [],
        "tool_calls": [],
        "text": choice.message.content or "",
    }

    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            result["tool_calls"].append({
                "id": tc.id,
                "name": tc.function.name,
                "input": json.loads(tc.function.arguments),
            })

    tokens = response.usage.total_tokens
    return result, tokens


def execute_tool(tool_name, tool_input, task, run):
    """Execute a tool and return the result."""
    from .models import TaskResult

    # Get user's API keys for premium tools
    user = task.workspace.owner
    skill_keys = getattr(user, 'skill_api_keys', None) or {}

    try:
        if tool_name == "web_search":
            return do_web_search(tool_input.get("query"), tool_input.get("num_results", 5))

        elif tool_name == "scrape_webpage":
            return do_scrape_webpage(tool_input.get("url"), tool_input.get("extract", "text"))

        elif tool_name == "firecrawl_scrape":
            api_key = skill_keys.get('FIRECRAWL_API_KEY')
            if not api_key:
                return "Error: FIRECRAWL_API_KEY not configured. Please add it in Settings > Skill API Keys."
            return do_firecrawl_scrape(
                api_key,
                tool_input.get("url"),
                tool_input.get("formats", ["markdown"])
            )

        elif tool_name == "firecrawl_search":
            api_key = skill_keys.get('FIRECRAWL_API_KEY')
            if not api_key:
                return "Error: FIRECRAWL_API_KEY not configured. Please add it in Settings > Skill API Keys."
            return do_firecrawl_search(
                api_key,
                tool_input.get("query"),
                tool_input.get("num_results", 5)
            )

        elif tool_name == "serper_jobs":
            api_key = skill_keys.get('SERPER_API_KEY')
            if not api_key:
                return "Error: SERPER_API_KEY not configured. Please add it in Settings > Skill API Keys."
            return do_serper_jobs(
                api_key,
                tool_input.get("query"),
                tool_input.get("location", ""),
                tool_input.get("num_results", 10)
            )

        elif tool_name == "search_jobs":
            # Use Serper if available (better results from Google Jobs)
            serper_key = skill_keys.get('SERPER_API_KEY')
            if serper_key:
                logger.info(f"Using Serper API for job search: {tool_input.get('query')}")
                return do_serper_jobs(
                    serper_key,
                    tool_input.get("query"),
                    tool_input.get("location", ""),
                    15
                )
            # Fall back to free APIs (RemoteOK, Remotive, Arbeitnow)
            logger.info(f"Using free APIs for job search (no SERPER_API_KEY): {tool_input.get('query')}")
            return do_search_jobs(
                tool_input.get("query"),
                tool_input.get("location", ""),
                tool_input.get("site", "all"),
            )

        elif tool_name == "send_message":
            return do_send_message(
                task.workspace,
                tool_input.get("message"),
                tool_input.get("format", "markdown"),
            )

        elif tool_name == "save_result":
            # Save to database
            TaskResult.objects.create(
                task=task,
                run=run,
                result_type=tool_input.get("type", "item"),
                title=tool_input.get("title", ""),
                url=tool_input.get("url", ""),
                score=tool_input.get("score"),
                summary=tool_input.get("summary", ""),
                data=tool_input.get("data", {}),
            )
            return "Result saved successfully."

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return f"Error executing {tool_name}: {str(e)}"


def do_web_search(query, num_results=5):
    """Perform a web search using DuckDuckGo (no API key needed)."""
    try:
        # Using DuckDuckGo HTML (simple scraping)
        url = "https://html.duckduckgo.com/html/"
        response = requests.post(url, data={"q": query}, timeout=10)
        response.raise_for_status()

        # Parse results (simplified)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        for result in soup.select('.result')[:num_results]:
            title_elem = result.select_one('.result__title')
            snippet_elem = result.select_one('.result__snippet')
            link_elem = result.select_one('.result__url')

            if title_elem:
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                    'url': link_elem.get_text(strip=True) if link_elem else '',
                })

        return json.dumps(results, indent=2)

    except Exception as e:
        return f"Search failed: {str(e)}"


def do_scrape_webpage(url, extract="text"):
    """Scrape content from a webpage."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove scripts and styles
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        if extract == "text":
            text = soup.get_text(separator='\n', strip=True)
            # Truncate if too long
            return text[:5000] + "..." if len(text) > 5000 else text

        elif extract == "links":
            links = []
            for a in soup.find_all('a', href=True)[:20]:
                links.append({
                    'text': a.get_text(strip=True),
                    'href': a['href'],
                })
            return json.dumps(links, indent=2)

        elif extract == "structured":
            # Try to extract job listing or article structure
            data = {
                'title': soup.title.string if soup.title else '',
                'headings': [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2'])[:5]],
                'paragraphs': [p.get_text(strip=True)[:200] for p in soup.find_all('p')[:5]],
            }
            return json.dumps(data, indent=2)

        return "Unknown extract mode"

    except Exception as e:
        return f"Scrape failed: {str(e)}"


def do_search_jobs(query, location="", site="all"):
    """Search for jobs using free job APIs (RemoteOK, Remotive, Arbeitnow)."""
    results = []
    query_lower = query.lower()
    sources_status = {}

    # 1. Search Remotive API
    try:
        logger.info(f"Searching Remotive for: {query}")
        remotive_url = f"https://remotive.com/api/remote-jobs?search={requests.utils.quote(query)}&limit=10"
        response = requests.get(remotive_url, timeout=15, headers={'User-Agent': 'JobAgent/1.0'})
        if response.ok:
            data = response.json()
            remotive_count = 0
            for job in data.get('jobs', [])[:5]:  # Reduced to 5
                results.append({
                    'title': job.get('title', '')[:80],
                    'company': job.get('company_name', '')[:50],
                    'location': job.get('candidate_required_location', 'Remote')[:40],
                    'url': job.get('url', ''),
                    'salary': job.get('salary', ''),
                    'source': 'remotive',
                })
                remotive_count += 1
            sources_status['remotive'] = remotive_count
            logger.info(f"Remotive returned {remotive_count} jobs")
        else:
            sources_status['remotive'] = 0
    except Exception as e:
        sources_status['remotive'] = 0
        logger.warning(f"Remotive API failed: {e}")

    # 2. Search RemoteOK API
    try:
        logger.info(f"Searching RemoteOK for: {query}")
        remoteok_url = "https://remoteok.com/api"
        response = requests.get(remoteok_url, timeout=15, headers={'User-Agent': 'JobAgent/1.0'})
        if response.ok:
            data = response.json()
            remoteok_count = 0
            for job in data[1:]:  # First item is metadata
                job_text = f"{job.get('position', '')} {job.get('company', '')} {' '.join(job.get('tags', []))}".lower()
                if any(q in job_text for q in query_lower.split()):
                    results.append({
                        'title': job.get('position', '')[:80],
                        'company': job.get('company', '')[:50],
                        'location': job.get('location', 'Remote')[:40],
                        'url': job.get('url', ''),
                        'salary': job.get('salary', ''),
                        'source': 'remoteok',
                    })
                    remoteok_count += 1
                if remoteok_count >= 5:  # Reduced to 5
                    break
            sources_status['remoteok'] = remoteok_count
            logger.info(f"RemoteOK returned {remoteok_count} matching jobs")
        else:
            sources_status['remoteok'] = 0
    except Exception as e:
        sources_status['remoteok'] = 0
        logger.warning(f"RemoteOK API failed: {e}")

    # 3. Search Arbeitnow API (EU/Remote jobs)
    try:
        logger.info(f"Searching Arbeitnow for: {query}")
        arbeitnow_url = "https://arbeitnow.com/api/job-board-api"
        response = requests.get(arbeitnow_url, timeout=15, headers={'User-Agent': 'JobAgent/1.0'})
        if response.ok:
            data = response.json()
            arbeitnow_count = 0
            for job in data.get('data', []):
                job_text = f"{job.get('title', '')} {job.get('company_name', '')}".lower()
                if any(q in job_text for q in query_lower.split()):
                    results.append({
                        'title': job.get('title', '')[:80],
                        'company': job.get('company_name', '')[:50],
                        'location': 'Remote' if job.get('remote') else job.get('location', '')[:40],
                        'url': job.get('url', ''),
                        'source': 'arbeitnow',
                    })
                    arbeitnow_count += 1
                if arbeitnow_count >= 3:  # Reduced to 3
                    break
            sources_status['arbeitnow'] = arbeitnow_count
        else:
            sources_status['arbeitnow'] = 0
    except Exception as e:
        sources_status['arbeitnow'] = 0
        logger.warning(f"Arbeitnow API failed: {e}")

    logger.info(f"Job search complete. Total: {len(results)}")

    if not results:
        return json.dumps({"error": "No jobs found", "query": query})

    return json.dumps({"jobs": results, "count": len(results)})


def do_firecrawl_scrape(api_key, url, formats=None):
    """
    Scrape a webpage using Firecrawl API.
    Works with JavaScript-rendered pages like LinkedIn, Indeed, Glassdoor.
    """
    if formats is None:
        formats = ["markdown"]

    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'url': url,
            'formats': formats,
            'onlyMainContent': True,
            'waitFor': 3000,  # Wait for JS to render
        }

        response = requests.post(
            'https://api.firecrawl.dev/v1/scrape',
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 402:
            return "Error: Firecrawl API quota exceeded or payment required."

        if not response.ok:
            return f"Firecrawl API error: {response.status_code} - {response.text[:200]}"

        data = response.json()

        if not data.get('success'):
            return f"Firecrawl scrape failed: {data.get('error', 'Unknown error')}"

        result = {
            'url': url,
            'title': data.get('data', {}).get('metadata', {}).get('title', ''),
            'description': data.get('data', {}).get('metadata', {}).get('description', ''),
        }

        # Add requested formats
        if 'markdown' in formats:
            result['markdown'] = data.get('data', {}).get('markdown', '')[:10000]
        if 'html' in formats:
            result['html'] = data.get('data', {}).get('html', '')[:10000]
        if 'links' in formats:
            result['links'] = data.get('data', {}).get('links', [])[:50]

        return json.dumps(result, indent=2)

    except requests.Timeout:
        return "Error: Firecrawl request timed out. The page may be too slow to load."
    except Exception as e:
        logger.error(f"Firecrawl scrape failed: {e}")
        return f"Firecrawl scrape failed: {str(e)}"


def do_firecrawl_search(api_key, query, num_results=5):
    """
    Search the web using Firecrawl and get scraped content from results.
    """
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'query': query,
            'limit': min(num_results, 10),
            'scrapeOptions': {
                'formats': ['markdown'],
                'onlyMainContent': True
            }
        }

        response = requests.post(
            'https://api.firecrawl.dev/v1/search',
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 402:
            return "Error: Firecrawl API quota exceeded or payment required."

        if not response.ok:
            return f"Firecrawl API error: {response.status_code} - {response.text[:200]}"

        data = response.json()

        if not data.get('success'):
            return f"Firecrawl search failed: {data.get('error', 'Unknown error')}"

        results = []
        for item in data.get('data', [])[:8]:  # Get more results
            results.append({
                'url': item.get('url', ''),
                'title': item.get('metadata', {}).get('title', '')[:150],
                'description': item.get('metadata', {}).get('description', '')[:300],
                'markdown': item.get('markdown', '')[:3000],  # More content for job analysis
            })

        return json.dumps(results)

    except requests.Timeout:
        return "Error: Firecrawl search timed out."
    except Exception as e:
        logger.error(f"Firecrawl search failed: {e}")
        return f"Firecrawl search failed: {str(e)}"


def do_serper_jobs(api_key, query, location="", num_results=10):
    """
    Search for jobs using Serper API (Google Search).
    Uses regular search with 'jobs' keyword to find job listings.
    """
    try:
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

        # Build job-focused search query
        search_query = f"{query} jobs"
        if location:
            search_query += f" {location}"

        payload = {
            'q': search_query,
            'num': min(num_results, 20),
        }

        response = requests.post(
            'https://google.serper.dev/search',
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 403:
            return "Error: Serper API key invalid or quota exceeded."

        if not response.ok:
            return f"Serper API error: {response.status_code} - {response.text[:200]}"

        data = response.json()

        # Extract job-related results from organic search
        results = []
        job_domains = ['linkedin.com/jobs', 'indeed.com', 'glassdoor.com', 'lever.co',
                      'greenhouse.io', 'wellfound.com', 'remoteok.com', 'weworkremotely.com']

        for item in data.get('organic', []):
            url = item.get('link', '')
            # Check if it's a job board URL
            is_job_url = any(domain in url.lower() for domain in job_domains)

            if is_job_url or 'job' in item.get('title', '').lower():
                results.append({
                    'title': item.get('title', '')[:80],
                    'company': '',  # Not available from search results
                    'location': 'See listing',
                    'url': url,
                    'description': item.get('snippet', '')[:200],
                    'source': 'google-search',
                })

            if len(results) >= 8:
                break

        if not results:
            return json.dumps({"error": "No job listings found", "query": search_query})

        return json.dumps({"jobs": results, "count": len(results)})

    except requests.Timeout:
        return "Error: Serper API request timed out."
    except Exception as e:
        logger.error(f"Serper search failed: {e}")
        return f"Serper search failed: {str(e)}"


def do_send_message(workspace, message, format="markdown"):
    """Send a message to connected channels."""
    sent_to = []

    # Try Telegram
    telegram_channel = workspace.channels.filter(
        channel_type='telegram',
        is_active=True
    ).first()

    logger.info(f"do_send_message: workspace={workspace.id}, channel found={telegram_channel is not None}")

    if telegram_channel:
        bot_token = telegram_channel.credentials.get('bot_token')
        chat_id = telegram_channel.credentials.get('chat_id')

        logger.info(f"Telegram credentials: has_token={bool(bot_token)}, has_chat_id={bool(chat_id)}")

        if bot_token and chat_id:
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                # Try without markdown first (more reliable)
                payload = {
                    'chat_id': chat_id,
                    'text': message[:4000],  # Telegram limit is 4096
                }
                response = requests.post(url, json=payload, timeout=10)
                logger.info(f"Telegram API response: {response.status_code} - {response.text[:200]}")
                if response.ok:
                    sent_to.append('telegram')
                else:
                    logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")

    if sent_to:
        return f"Message sent via: {', '.join(sent_to)}"
    else:
        return "No channels configured or message sending failed. The message was: " + message[:200]


def send_job_results_notification(task, jobs, run):
    """Send a summary of job search results to connected channels."""
    if not jobs:
        return

    workspace = task.workspace

    # Build message
    message = f"🔎 *Job Search Complete*\n\n"
    message += f"Found {len(jobs)} jobs matching your criteria.\n\n"

    # Sort by score if available
    sorted_jobs = sorted(jobs, key=lambda x: x.get('score', 0), reverse=True)

    for i, job in enumerate(sorted_jobs[:10], 1):
        title = job.get('title', 'Untitled')
        company = job.get('company', 'Unknown')
        location = job.get('location', '')
        salary = job.get('salary', '') or ''
        url = job.get('job_url', '') or job.get('url', '')
        source = job.get('source', '')
        score = job.get('score', 0)
        matched = job.get('matched_keywords', [])

        # Score badge
        if score >= 70:
            score_badge = f"⭐ {score}/100"
        elif score >= 40:
            score_badge = f"✓ {score}/100"
        else:
            score_badge = f"{score}/100"

        message += f"*{i}. {title}* {score_badge}\n"
        message += f"   🏢 {company}\n"
        if location:
            message += f"   📍 {location}\n"
        if salary:
            message += f"   💰 {salary}\n"
        if matched:
            message += f"   🏷️ {', '.join(matched[:3])}\n"
        if source:
            message += f"   📌 {source}\n"
        if url:
            message += f"   🔗 {url[:60]}...\n"
        message += "\n"

    if len(jobs) > 10:
        message += f"\n...and {len(jobs) - 10} more jobs saved.\n"

    message += f"\n✅ All results saved to dashboard. View full list at /dashboard/workspaces/{workspace.id}/results"

    # Send via do_send_message
    result = do_send_message(workspace, message, "markdown")
    logger.info(f"Job results notification sent: {result}")

    return result


# =============================================================================
# PIPELINE-BASED JOB SEARCH (Much more efficient than agentic loop)
# =============================================================================

JOB_ANALYSIS_PROMPT = """Analyze this job for a SOFTWARE DEVELOPER role using AI tools.

Search terms: {search_terms}
{location_filter}

REQUIREMENTS (score 0 if ANY fails):
1. Must be developer/engineer role (full-stack, software, frontend, backend, web, mobile)
2. Should USE AI coding tools (Claude Code, Cursor, Copilot, AI pair programming) - NOT be a job about BUILDING AI
3. Must involve hands-on coding work
{location_scoring}

IMPORTANT: "Remote" or "Remote - US" or "Work from home" counts as is_remote:true!

Score guide:
- 90-100: Perfect - explicitly mentions AI coding tools (Copilot, Cursor, Claude Code)
- 80-89: Great - AI/LLM startup that would naturally use AI tools
- 70-79: Good - modern dev role with progressive tooling
- 50-69: Partial match
- 0-49: Poor match, wrong role type, or job is about BUILDING AI (Anthropic, OpenAI core roles)

Reply with ONLY this JSON (no other text):
{{"score":0,"reason":"","title":"","company":"","location":"","is_remote":false,"role_type":"","skills_matched":[]}}

Job posting:
{job_text}"""


def build_dork_queries(search_terms: list, sites: list = None, location: str = None) -> list:
    """Build Google Dork queries for job sites (like the standalone script)."""
    if sites is None:
        sites = JOB_SITES[:5]  # Limit to top 5 sites to avoid too many queries

    queries = []

    # Group terms for OR queries (max 3 per query)
    term_groups = [search_terms[i:i+3] for i in range(0, len(search_terms), 3)]

    # Build location suffix
    location_suffix = ""
    if location and location.lower() != 'remote':
        location_suffix = f' ("{location}" OR "remote")'
    elif location and location.lower() == 'remote':
        location_suffix = ' ("remote" OR "work from home")'

    for site in sites:
        for group in term_groups[:2]:  # Limit groups per site
            # Build OR query with quoted terms
            or_terms = ' OR '.join(f'"{term}"' for term in group)
            query = f'site:{site} {or_terms}{location_suffix}'
            queries.append(query)

    return queries


def is_job_url(url: str) -> bool:
    """Check if URL is an actual job posting (not a search/category page)."""
    # Must match SPECIFIC job posting patterns
    actual_job_patterns = [
        "linkedin.com/jobs/view/",      # Individual LinkedIn job
        "indeed.com/viewjob",
        "indeed.com/job/",
        "indeed.com/rc/clk",             # Indeed redirect to job
        "lever.co/",                      # Lever jobs (company/job-id format)
        "greenhouse.io/",                 # Greenhouse jobs
        "boards.greenhouse.io/",
        "job-boards.greenhouse.io/",
        "jobs.ashbyhq.com/",             # Ashby jobs
        "wellfound.com/jobs/",           # Wellfound with job ID
        "angel.co/company/",
        "workatastartup.com/jobs/",
        "remoteok.com/remote-jobs/remote-",  # Specific RemoteOK job
        "weworkremotely.com/remote-jobs/",
        "builtin.com/job/",
    ]

    # Exclude search/category pages
    exclude_patterns = [
        "linkedin.com/jobs/search",
        "linkedin.com/jobs/collections",
        "linkedin.com/jobs?",             # Search with params
        "-jobs?",                         # Category pages
        "/jobs?keywords=",
    ]

    url_lower = url.lower()

    # Check exclusions first
    for exclude in exclude_patterns:
        if exclude in url_lower:
            return False

    # Check if it matches actual job patterns
    for pattern in actual_job_patterns:
        if pattern in url_lower:
            return True

    return False


def is_job_search_page(url: str) -> bool:
    """Check if URL is a job search/category page (not individual job)."""
    search_patterns = [
        "linkedin.com/jobs/",
        "indeed.com/jobs",
        "indeed.com/q-",
    ]
    url_lower = url.lower()

    # It's a search page if it matches search patterns but NOT individual job patterns
    if any(p in url_lower for p in search_patterns):
        if not is_job_url(url):
            return True
    return False


def extract_job_urls_from_search_results(search_results: list, found_urls: set) -> list:
    """Extract job URLs from search results, avoiding duplicates."""
    import re
    from urllib.parse import unquote

    job_urls = []

    for result in search_results:
        url = result.get('url', '') or result.get('link', '')
        if not url:
            continue

        # Decode URL-encoded characters
        url = unquote(url)

        # Extract from Google redirect URLs
        if "/url?q=" in url:
            match = re.search(r'/url\?q=([^&]+)', url)
            if match:
                url = unquote(match.group(1))

        # Normalize URL (remove fragments and some params)
        base_url = url.split('#')[0]
        if '?' in base_url:
            # Keep the URL but normalize
            pass

        if is_job_url(url) and base_url not in found_urls:
            job_urls.append(url)
            found_urls.add(base_url)

    return job_urls


def parse_job_search_instructions(instructions: str) -> dict:
    """Extract search parameters from natural language instructions."""
    import re

    result = {
        'search_terms': [],
        'location': None,
        'job_titles': [],
        'sites': [],
        'wants_ai_tools': False,  # Does user want jobs requiring AI coding tools?
    }

    instructions_lower = instructions.lower()

    # Check if user wants AI coding tool jobs
    ai_tool_indicators = [
        'claude code', 'claude-code', 'copilot', 'github copilot',
        'ai coding', 'ai assistant', 'cursor', 'codeium', 'ai pair',
        'ai tools', 'ai-native', 'uses ai', 'require ai'
    ]
    result['wants_ai_tools'] = any(term in instructions_lower for term in ai_tool_indicators)

    # Extract quoted terms
    quoted = re.findall(r'"([^"]+)"', instructions)
    result['search_terms'] = quoted if quoted else []

    # Extract location patterns
    location_patterns = [
        r'(?:in|near|at|location[:\s]+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'(?:remote|work from home|wfh)',
    ]
    for pattern in location_patterns:
        match = re.search(pattern, instructions, re.IGNORECASE)
        if match:
            result['location'] = match.group(1) if match.lastindex else 'Remote'
            break

    # Extract job title patterns
    title_patterns = [
        r'(AI Engineer|Software Engineer|Developer|Full[- ]?Stack|Backend|Frontend|Data Scientist)',
    ]
    for pattern in title_patterns:
        matches = re.findall(pattern, instructions, re.IGNORECASE)
        result['job_titles'].extend(matches)

    # If no specific terms found, extract key phrases
    if not result['search_terms']:
        # Remove common words and extract meaningful terms
        words = instructions_lower.split()
        keywords = [w for w in words if len(w) > 4 and w not in
                   ['search', 'find', 'looking', 'jobs', 'postings', 'these', 'criteria', 'titles', 'with']]
        result['search_terms'] = keywords[:5]

    return result


def analyze_single_job(api_key: str, job_data: dict, search_terms: list, location: str = None) -> dict:
    """Analyze a single job with ONE Claude call. Returns score and analysis."""
    import anthropic

    # Build job text from available data
    job_text = f"""
Title: {job_data.get('title', 'Unknown')}
Company: {job_data.get('company', 'Unknown')}
Location: {job_data.get('location', 'Unknown')}
Description: {job_data.get('description', '')[:1500]}
URL: {job_data.get('url', '')}
"""

    # Build prompt
    terms_str = ', '.join(search_terms) if search_terms else 'software developer jobs'
    location_filter = f"Preferred location: {location} (remote also OK)" if location else ""

    prompt = JOB_ANALYSIS_PROMPT.format(
        search_terms=terms_str,
        location_filter=location_filter,
        job_text=job_text
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text.strip()

        # Extract JSON
        import re
        json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group(0))
            # Merge with original job data
            return {
                **job_data,
                'score': analysis.get('score', 0),
                'analysis_title': analysis.get('title', job_data.get('title', '')),
                'analysis_company': analysis.get('company', job_data.get('company', '')),
                'analysis_location': analysis.get('location', job_data.get('location', '')),
                'is_remote': analysis.get('is_remote', False),
                'reason': analysis.get('reason', ''),
                'key_skills': analysis.get('key_skills', []),
            }
    except Exception as e:
        logger.error(f"Job analysis failed: {e}")

    return {**job_data, 'score': 0, 'reason': 'Analysis failed'}


def execute_job_search_pipeline(task_id: int):
    """
    Pipeline-based job search with multiple strategies:

    Priority order:
    1. JobSpy (FREE) - Scrapes LinkedIn, Indeed, Glassdoor directly
    2. Gateway Browser - Uses Playwright in OpenClaw container
    3. Serper + Firecrawl APIs - Fallback for when above fail

    JobSpy is now the primary method since it's free and works with LinkedIn/Indeed.
    """
    from .models import AgentTask, TaskRun, TaskResult

    try:
        task = AgentTask.objects.select_related('workspace', 'workspace__owner').get(id=task_id)
    except AgentTask.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return

    workspace = task.workspace
    user = workspace.owner

    # Get API keys
    anthropic_key = user.anthropic_api_key
    if not anthropic_key:
        task.last_error = "No Anthropic API key configured"
        task.save()
        return

    skill_keys = user.skill_api_keys or {}
    serper_key = skill_keys.get('SERPER_API_KEY')
    firecrawl_key = skill_keys.get('FIRECRAWL_API_KEY')

    # Create run record
    run = TaskRun.objects.create(task=task, status='running')
    task.status = AgentTask.Status.RUNNING
    task.save()

    logger.info(f"Starting job search pipeline for task {task_id}")
    logger.info(f"API keys available - Serper: {bool(serper_key)}, Firecrawl: {bool(firecrawl_key)}")

    try:
        # Step 1: Parse instructions
        params = parse_job_search_instructions(task.instructions)
        location = params['location']
        wants_ai_tools = params.get('wants_ai_tools', False)

        # Use AI tool search terms if requested, otherwise use parsed terms
        if wants_ai_tools:
            search_terms = DEFAULT_AI_SEARCH_TERMS
            logger.info(f"Using AI tool search terms: {search_terms}")
        else:
            search_terms = params['search_terms'] or ['software engineer', 'developer']

        logger.info(f"Search terms: {search_terms}, Location: {location}, AI tools: {wants_ai_tools}")

        # =================================================================
        # PRIORITY 1: Use JobSpy (FREE - scrapes LinkedIn/Indeed directly)
        # =================================================================
        jobspy_results = []
        try:
            search_query = ' '.join(search_terms[:3])  # Combine first 3 terms
            logger.info(f"Trying JobSpy search: '{search_query}' in '{location}'")

            jobspy_result = scrape_jobs_with_jobspy(
                search_term=search_query,
                location=location if location else 'remote',
                sites=['indeed', 'linkedin', 'glassdoor'],
                results_wanted=30,
                is_remote=(location.lower() == 'remote' if location else True)
            )

            if jobspy_result['success'] and jobspy_result['jobs']:
                jobspy_results = jobspy_result['jobs']
                logger.info(f"JobSpy found {len(jobspy_results)} jobs from LinkedIn/Indeed/Glassdoor!")

                # Save JobSpy results with AI tools scoring
                jobs_saved = 0
                scored_jobs = []

                for job in jobspy_results:
                    # Calculate match score based on AI tools keywords
                    job_score, matched_keywords = calculate_job_score(job)
                    job['score'] = job_score
                    job['matched_keywords'] = matched_keywords
                    scored_jobs.append(job)

                # Sort by score (highest first)
                scored_jobs.sort(key=lambda x: x.get('score', 0), reverse=True)

                for job in scored_jobs:
                    try:
                        # Build salary string
                        salary = ""
                        if job.get('salary_min') and job.get('salary_max'):
                            interval = job.get('salary_interval', 'yearly')
                            salary = f"${job['salary_min']:,.0f} - ${job['salary_max']:,.0f} {interval}"

                        TaskResult.objects.create(
                            task=task,
                            run=run,
                            result_type="job",
                            title=job.get('title', 'Untitled'),
                            url=job.get('job_url', ''),
                            score=job.get('score', 0),  # Store the AI tools match score
                            summary=f"Matched: {', '.join(job.get('matched_keywords', [])[:5])}" if job.get('matched_keywords') else "",
                            data={
                                'company': job.get('company', ''),
                                'location': job.get('location', ''),
                                'salary': salary,
                                'job_type': job.get('job_type', ''),
                                'is_remote': job.get('is_remote', False),
                                'source': f"JobSpy:{job.get('source', '')}",
                                'date_posted': job.get('date_posted', ''),
                                'description': job.get('description', '')[:500] if job.get('description') else '',
                                'matched_keywords': job.get('matched_keywords', []),
                                'match_score': job.get('score', 0),
                            }
                        )
                        jobs_saved += 1
                    except Exception as e:
                        logger.error(f"Failed to save JobSpy result: {e}")

                # If JobSpy found enough results, complete the task
                if jobs_saved >= 10:
                    run.status = "completed"
                    run.completed_at = timezone.now()
                    run.result = f"Found {jobs_saved} jobs via JobSpy (LinkedIn/Indeed/Glassdoor)"
                    run.result_data = {'jobs_count': jobs_saved, 'source': 'jobspy'}
                    run.save()

                    task.status = AgentTask.Status.COMPLETED
                    task.last_run = timezone.now()
                    task.run_count += 1
                    task.last_result = f"Found {jobs_saved} jobs via JobSpy"
                    task.save()

                    # Send Telegram notification
                    send_job_results_notification(task, jobspy_results[:10], run)

                    logger.info(f"JobSpy job search completed: saved {jobs_saved} jobs")
                    return {'success': True, 'jobs_count': jobs_saved, 'source': 'jobspy'}

            else:
                logger.warning(f"JobSpy returned no results, falling back to other methods")

        except Exception as e:
            logger.warning(f"JobSpy search failed: {e}, falling back to other methods")
            import traceback
            traceback.print_exc()

        # =================================================================
        # PRIORITY 2: Try OpenClaw Gateway (uses installed Playwright skill)
        # =================================================================
        job_urls_to_scrape = []
        gateway_url = get_workspace_gateway_url(workspace)

        from workspaces.models import Workspace as WS
        if gateway_url and workspace.status == WS.Status.RUNNING:
            logger.info(f"Workspace is running, trying Gateway browser search...")
            logger.info(f"Gateway URL: {gateway_url}")

            try:
                # Use Gateway browser for search (like standalone script)
                gateway_jobs = run_gateway_job_search(workspace, search_terms, location)

                if gateway_jobs:
                    logger.info(f"Gateway search found {len(gateway_jobs)} jobs with content!")
                    job_urls_to_scrape = gateway_jobs
                else:
                    logger.warning("Gateway search returned no jobs, falling back to APIs")

            except Exception as e:
                logger.error(f"Gateway search failed: {e}, falling back to APIs")
                import traceback
                traceback.print_exc()
        else:
            logger.info(f"Workspace not running (status: {workspace.status}), using API fallback")

        # =================================================================
        # FALLBACK: Use Serper/Firecrawl APIs if Gateway didn't work
        # =================================================================
        found_urls = set()
        search_pages_to_scrape = []

        if not job_urls_to_scrape and wants_ai_tools:
            logger.info("Using API fallback for job search...")

            # Build site-specific dork queries (like the standalone script)
            dork_queries = build_dork_queries(search_terms[:4], JOB_SITES[:6], location)
            logger.info(f"Built {len(dork_queries)} dork queries")

            # PRIMARY: Use Firecrawl search (actually browses pages, better results)
            if firecrawl_key:
                logger.info("Using Firecrawl search (browser-based, better results)...")
                for i, query in enumerate(dork_queries[:5]):  # Limit to 5 queries
                    logger.info(f"Firecrawl query {i+1}: {query[:50]}...")
                    try:
                        fc_result = do_firecrawl_search(firecrawl_key, query, 5)
                        fc_data = json.loads(fc_result)

                        # Firecrawl returns array directly or might have 'results' key
                        results_list = fc_data if isinstance(fc_data, list) else fc_data.get('results', fc_data.get('data', []))
                        if results_list:
                            for result in results_list:
                                url = result.get('url', '')
                                if is_job_url(url):
                                    base_url = url.split('#')[0]
                                    if base_url not in found_urls:
                                        found_urls.add(base_url)
                                        job_urls_to_scrape.append({
                                            'url': url,
                                            'title': result.get('title', ''),
                                            'snippet': result.get('description', ''),
                                            'content': result.get('markdown', '')[:3000],  # Firecrawl gives full content!
                                        })
                                        logger.info(f"  [Firecrawl] Found: {url[:60]}...")
                                elif is_job_search_page(url):
                                    # This is a search results page - we can extract jobs from it
                                    if url not in search_pages_to_scrape:
                                        search_pages_to_scrape.append(url)
                                        logger.info(f"  [Firecrawl] Found search page to scrape: {url[:50]}...")

                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Firecrawl search failed: {e}")

            # SECONDARY: Use Serper as fallback
            if serper_key and len(job_urls_to_scrape) < 10:
                logger.info("Using Serper search as supplement...")
                for i, query in enumerate(dork_queries[:4]):
                    logger.info(f"Serper query {i+1}: {query[:50]}...")
                    try:
                        headers = {
                            'X-API-KEY': serper_key,
                            'Content-Type': 'application/json'
                        }
                        payload = {'q': query, 'num': 15}
                        response = requests.post(
                            'https://google.serper.dev/search',
                            headers=headers,
                            json=payload,
                            timeout=30
                        )

                        if response.ok:
                            data = response.json()
                            organic = data.get('organic', [])

                            for result in organic:
                                url = result.get('link', '')
                                if is_job_url(url):
                                    base_url = url.split('#')[0]
                                    if base_url not in found_urls:
                                        found_urls.add(base_url)
                                        job_urls_to_scrape.append({
                                            'url': url,
                                            'title': result.get('title', ''),
                                            'snippet': result.get('snippet', ''),
                                        })
                                        logger.info(f"  [Serper] Found: {url[:60]}...")
                                elif is_job_search_page(url):
                                    if url not in search_pages_to_scrape:
                                        search_pages_to_scrape.append(url)

                        time.sleep(0.3)
                    except Exception as e:
                        logger.error(f"Serper query failed: {e}")

            # STEP 2b: Scrape search results pages to extract more job URLs
            if firecrawl_key and search_pages_to_scrape and len(job_urls_to_scrape) < 15:
                logger.info(f"Scraping {len(search_pages_to_scrape)} search pages for job links...")
                for page_url in search_pages_to_scrape[:3]:  # Limit to 3 pages
                    try:
                        scrape_result = do_firecrawl_scrape(firecrawl_key, page_url, ['links', 'markdown'])
                        scrape_data = json.loads(scrape_result)
                        links = scrape_data.get('links', [])

                        for link in links:
                            if isinstance(link, str) and is_job_url(link):
                                base_url = link.split('#')[0]
                                if base_url not in found_urls:
                                    found_urls.add(base_url)
                                    job_urls_to_scrape.append({
                                        'url': link,
                                        'title': '',
                                        'snippet': '',
                                    })
                                    logger.info(f"  [From search page] Found: {link[:60]}...")

                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Failed to scrape search page {page_url[:40]}: {e}")

            logger.info(f"Found {len(job_urls_to_scrape)} unique job URLs from dork queries")

        # Also use standard Serper jobs endpoint as fallback
        if serper_key and len(job_urls_to_scrape) < 5:
            logger.info("Using Serper jobs endpoint as fallback...")
            simple_query = ' '.join(search_terms[:3])
            if wants_ai_tools:
                simple_query = "software engineer AI tools remote"

            serper_result = do_serper_jobs(serper_key, simple_query, location or '', 15)
            try:
                data = json.loads(serper_result)
                if 'jobs' in data:
                    for job in data['jobs']:
                        url = job.get('url', '')
                        if url:
                            base_url = url.split('#')[0].split('?')[0]
                            if base_url not in found_urls:
                                found_urls.add(base_url)
                                job_urls_to_scrape.append({
                                    'url': url,
                                    'title': job.get('title', ''),
                                    'company': job.get('company', ''),
                                    'location': job.get('location', ''),
                                    'snippet': job.get('description', ''),
                                })
                    logger.info(f"Serper jobs added {len(data['jobs'])} more URLs")
            except:
                pass

        # Also search free APIs
        logger.info("Searching free APIs (Remotive, RemoteOK)...")
        free_result = do_search_jobs(' '.join(search_terms[:3]), location or '', 'all')
        try:
            data = json.loads(free_result)
            if 'jobs' in data:
                for job in data['jobs']:
                    url = job.get('url', '')
                    if url:
                        base_url = url.split('#')[0].split('?')[0]
                        if base_url not in found_urls:
                            found_urls.add(base_url)
                            job_urls_to_scrape.append({
                                'url': url,
                                'title': job.get('title', ''),
                                'company': job.get('company', ''),
                                'location': job.get('location', ''),
                                'snippet': job.get('description', ''),
                            })
                logger.info(f"Free APIs added {len(data['jobs'])} URLs")
        except:
            pass

        if not job_urls_to_scrape:
            logger.warning("No job URLs found from any source")
            do_send_message(workspace, f"No jobs found for: {', '.join(search_terms)}", "text")
            run.status = 'completed'
            run.completed_at = timezone.now()
            run.agent_reasoning = "No jobs found"
            run.save()
            task.status = AgentTask.Status.COMPLETED
            task.last_run = timezone.now()
            task.save()
            return

        logger.info(f"Total job URLs to process: {len(job_urls_to_scrape)}")

        # Step 3: Scrape job pages and analyze (like the standalone script)
        analyzed_jobs = []
        tokens_used = 0
        max_jobs = 15  # Increased limit for better coverage

        for i, job_data in enumerate(job_urls_to_scrape[:max_jobs]):
            url = job_data.get('url', '')
            logger.info(f"Processing job {i+1}/{min(len(job_urls_to_scrape), max_jobs)}: {url[:50]}...")

            # Get full job content - check if we already have it from Firecrawl search
            job_content = job_data.get('content', '')

            if job_content and len(job_content) > 500:
                logger.info(f"  Using pre-scraped content ({len(job_content)} chars)")
            else:
                # Need to scrape the page
                # Use Firecrawl for JavaScript-heavy sites
                js_sites = ['linkedin.com', 'indeed.com', 'greenhouse.io', 'lever.co', 'ashbyhq.com', 'wellfound.com']
                if firecrawl_key and any(site in url for site in js_sites):
                    logger.info("  Scraping with Firecrawl...")
                    try:
                        scrape_result = do_firecrawl_scrape(firecrawl_key, url, ['markdown'])
                        scrape_data = json.loads(scrape_result)
                        job_content = scrape_data.get('markdown', '')[:4000]
                        if job_content:
                            logger.info(f"  Got {len(job_content)} chars from Firecrawl")
                    except Exception as e:
                        logger.warning(f"  Firecrawl failed: {e}")
                    time.sleep(0.3)  # Rate limit

            # Fall back to snippet/metadata if no full content
            if not job_content or len(job_content) < 200:
                job_content = f"""
Title: {job_data.get('title', 'Unknown')}
Company: {job_data.get('company', 'Unknown')}
Location: {job_data.get('location', 'Unknown')}
Description: {job_data.get('snippet', '')}
URL: {url}
"""
                logger.info(f"  Using snippet data ({len(job_content)} chars)")

            # Analyze with Claude
            logger.info("  Analyzing with Claude...")
            analysis = analyze_single_job_content(anthropic_key, job_content, search_terms, location, url)
            tokens_used += 500  # Estimate ~500 tokens per analysis with full content

            score = analysis.get('score', 0)
            reason = analysis.get('reason', '')[:50]
            logger.info(f"  -> Score: {score}, Reason: {reason}")

            if score >= 50:  # Save jobs scoring 50+
                analysis['url'] = url
                analysis['source'] = detect_job_source(url)
                analyzed_jobs.append(analysis)

                # Save to database
                TaskResult.objects.create(
                    task=task,
                    run=run,
                    result_type='job',
                    title=analysis.get('title', 'Unknown'),
                    url=url,
                    score=score,
                    summary=analysis.get('reason', ''),
                    data={
                        'company': analysis.get('company', ''),
                        'location': analysis.get('location', ''),
                        'is_remote': analysis.get('is_remote', False),
                        'role_type': analysis.get('role_type', ''),
                        'skills_matched': analysis.get('skills_matched', []),
                        'source': analysis.get('source', ''),
                    }
                )

            time.sleep(0.5)  # Rate limit

        # Step 4: Sort by score
        analyzed_jobs.sort(key=lambda x: x.get('score', 0), reverse=True)

        # Step 5: Build and send summary
        if analyzed_jobs:
            summary = f"🔍 Found {len(analyzed_jobs)} matching jobs:\n\n"
            for job in analyzed_jobs[:10]:
                score = job.get('score', 0)
                title = job.get('title', 'Unknown')[:40]
                company = job.get('company', '')[:25]
                loc = '🌍 Remote' if job.get('is_remote') else f"📍 {job.get('location', '')[:15]}"
                url = job.get('url', '')
                source = job.get('source', '')

                summary += f"[{score}] {title}\n"
                if company:
                    summary += f"   {company} | {loc}"
                    if source:
                        summary += f" ({source})"
                    summary += "\n"
                if url:
                    summary += f"   {url}\n"
                summary += "\n"
        else:
            summary = f"No jobs matched your criteria (searched: {', '.join(search_terms[:3])})\n"
            summary += f"Processed {len(job_urls_to_scrape)} job listings."

        logger.info(f"Sending summary to Telegram...")
        send_result = do_send_message(workspace, summary, "text")
        logger.info(f"Send result: {send_result}")

        # Update run record
        run.status = 'completed'
        run.completed_at = timezone.now()
        run.agent_reasoning = f"Found {len(analyzed_jobs)} jobs from {len(job_urls_to_scrape)} URLs, used ~{tokens_used} tokens"
        run.tools_used = ['dork_queries', 'serper', 'firecrawl', 'analyze', 'send_message']
        run.tokens_used = tokens_used
        run.save()

        # Update task
        task.status = AgentTask.Status.COMPLETED
        task.last_run = timezone.now()
        task.run_count += 1
        task.last_result = summary[:500]
        task.last_error = ''
        task.save()

        logger.info(f"Pipeline completed. Found {len(analyzed_jobs)} jobs, ~{tokens_used} tokens used")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

        run.status = 'failed'
        run.completed_at = timezone.now()
        run.error_message = str(e)
        run.save()

        task.status = AgentTask.Status.FAILED
        task.last_error = str(e)
        task.save()


def detect_job_source(url: str) -> str:
    """Detect the job source from URL."""
    sources = {
        "linkedin.com": "LinkedIn",
        "indeed.com": "Indeed",
        "lever.co": "Lever",
        "greenhouse.io": "Greenhouse",
        "ashbyhq.com": "Ashby",
        "wellfound.com": "Wellfound",
        "workatastartup.com": "YC",
        "remoteok.com": "RemoteOK",
        "weworkremotely.com": "WWR",
        "builtin.com": "BuiltIn",
    }
    for domain, source in sources.items():
        if domain in url:
            return source
    return "Other"


def analyze_single_job_content(api_key: str, job_content: str, search_terms: list, location: str, url: str) -> dict:
    """Analyze full job content (up to 4000 chars) with Claude."""
    import anthropic

    terms_str = ', '.join(search_terms) if search_terms else 'software developer AI tools'

    # Build location-specific prompt parts
    if location:
        location_filter = f"Location filter: {location} OR ANY Remote/WFH"
        location_scoring = f"4. Location OK if: in {location}, OR remote/WFH anywhere"
    else:
        location_filter = "Location: Remote preferred"
        location_scoring = ""

    prompt = JOB_ANALYSIS_PROMPT.format(
        search_terms=terms_str,
        location_filter=location_filter,
        location_scoring=location_scoring,
        job_text=job_content[:4000]
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text.strip()

        # Extract JSON
        import re
        json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group(0))
            return analysis

    except Exception as e:
        logger.error(f"Job analysis failed: {e}")

    return {'score': 0, 'reason': 'Analysis failed', 'title': 'Unknown'}


@shared_task
def run_scheduled_tasks():
    """
    Run all scheduled tasks that are due.
    Called by Celery Beat.
    """
    from .models import AgentTask

    now = timezone.now()

    tasks = AgentTask.objects.filter(
        status=AgentTask.Status.PENDING,
    ).exclude(schedule=AgentTask.Schedule.ONCE)

    for task in tasks:
        should_run = False

        if not task.last_run:
            should_run = True
        else:
            time_since_last = now - task.last_run

            if task.schedule == 'hourly' and time_since_last > timedelta(hours=1):
                should_run = True
            elif task.schedule == 'daily' and time_since_last > timedelta(days=1):
                should_run = True
            elif task.schedule == 'weekly' and time_since_last > timedelta(weeks=1):
                should_run = True

        if should_run:
            execute_agent_task.delay(task.id)


# =============================================================================
# Browser-Based Job Scraping with Anti-Detection
# =============================================================================

# Job board configurations with anti-detection settings
JOB_BOARD_CONFIGS = {
    "remoteok": {
        "url": "https://remoteok.com/remote-dev-jobs",
        "search_url": "https://remoteok.com/remote-{query}-jobs",
        "delay_min": 2,
        "delay_max": 5,
        "requires_js": False,
        "bot_friendly": True,
    },
    "linkedin": {
        "url": "https://www.linkedin.com/jobs/search",
        "search_url": "https://www.linkedin.com/jobs/search?keywords={query}&location={location}&f_WT=2",
        "delay_min": 5,
        "delay_max": 10,
        "requires_js": True,
        "bot_friendly": False,
        "notes": "Requires browser-use cloud API or logged-in session for best results",
    },
    "indeed": {
        "url": "https://www.indeed.com/jobs",
        "search_url": "https://www.indeed.com/jobs?q={query}&l={location}&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11",
        "delay_min": 5,
        "delay_max": 10,
        "requires_js": True,
        "bot_friendly": False,
        "notes": "Heavy bot detection - use Google Jobs API instead",
    },
    "weworkremotely": {
        "url": "https://weworkremotely.com/remote-jobs",
        "search_url": "https://weworkremotely.com/remote-jobs/search?term={query}",
        "delay_min": 2,
        "delay_max": 4,
        "requires_js": False,
        "bot_friendly": True,
    },
    "builtin": {
        "url": "https://builtin.com/jobs/remote",
        "search_url": "https://builtin.com/jobs/remote?search={query}",
        "delay_min": 3,
        "delay_max": 6,
        "requires_js": True,
        "bot_friendly": True,
    },
}


@shared_task
def scrape_jobs_with_browser_task(task_id: int, job_boards: list = None, query: str = None):
    """
    Celery task to scrape job listings using browser automation.
    Uses direct browser control via OpenClaw Gateway.

    Args:
        task_id: AgentTask ID
        job_boards: List of job boards to scrape (default: bot-friendly ones)
        query: Search query (extracted from task instructions if not provided)
    """
    from .models import AgentTask, TaskRun, TaskResult
    from workspaces.models import Workspace

    try:
        task = AgentTask.objects.select_related('workspace', 'workspace__owner').get(id=task_id)
    except AgentTask.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return {"success": False, "error": "Task not found"}

    workspace = task.workspace

    # Check workspace is running
    if workspace.status != Workspace.Status.RUNNING:
        logger.error(f"Workspace {workspace.id} not running")
        return {"success": False, "error": "Workspace not running"}

    # Get Gateway connection info
    gateway_url, gateway_token = get_workspace_gateway_info(workspace)
    if not gateway_url:
        logger.error("Could not get gateway URL")
        return {"success": False, "error": "Gateway not available"}

    # Create run record
    run = TaskRun.objects.create(task=task, status='running')
    task.status = AgentTask.Status.RUNNING
    task.save()

    # Extract search query from task instructions if not provided
    if not query:
        query = extract_search_query(task.instructions)

    # Default to bot-friendly job boards if none specified
    if not job_boards:
        job_boards = ["remoteok", "weworkremotely", "builtin"]

    logger.info(f"Starting browser job scraping: query='{query}', boards={job_boards}")

    async def _scrape():
        gateway = OpenClawGatewayClient(gateway_url, gateway_token)
        all_jobs = []
        errors = []

        try:
            if not await gateway.connect():
                return {"success": False, "error": "Gateway connection failed", "jobs": []}

            for board_name in job_boards:
                config = JOB_BOARD_CONFIGS.get(board_name)
                if not config:
                    logger.warning(f"Unknown job board: {board_name}")
                    continue

                if not config.get("bot_friendly", True):
                    logger.warning(f"Skipping {board_name} - heavy bot detection. Use Google Jobs API instead.")
                    continue

                # Build search URL
                url = config["search_url"].format(
                    query=query.replace(" ", "-").lower(),
                    location="remote"
                )

                logger.info(f"Scraping {board_name}: {url}")

                try:
                    result = await scrape_jobs_with_browser(gateway, url)

                    if result["success"]:
                        for job in result["jobs"]:
                            job["source_board"] = board_name
                        all_jobs.extend(result["jobs"])
                        logger.info(f"Found {len(result['jobs'])} jobs from {board_name}")
                    else:
                        errors.append(f"{board_name}: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"Error scraping {board_name}: {e}")
                    errors.append(f"{board_name}: {str(e)}")

                # Anti-detection: Add random delay between sites
                import random
                delay = random.uniform(config["delay_min"], config["delay_max"])
                await asyncio.sleep(delay)

        finally:
            await gateway.disconnect()

        return {
            "success": len(all_jobs) > 0,
            "jobs": all_jobs,
            "errors": errors,
            "total_found": len(all_jobs)
        }

    # Run async scraping
    try:
        result = asyncio.run(_scrape())
    except Exception as e:
        logger.error(f"Browser scraping failed: {e}")
        result = {"success": False, "error": str(e), "jobs": []}

    # Save results
    jobs_saved = 0
    for job_data in result.get("jobs", []):
        try:
            TaskResult.objects.create(
                task=task,
                run=run,
                result_type="job",
                title=job_data.get("title", "Untitled"),
                url=job_data.get("url", ""),
                data={
                    "company": job_data.get("company", ""),
                    "salary": job_data.get("salary", ""),
                    "source": job_data.get("source", ""),
                    "source_board": job_data.get("source_board", ""),
                }
            )
            jobs_saved += 1
        except Exception as e:
            logger.error(f"Failed to save job result: {e}")

    # Update task and run
    run.status = "completed" if result["success"] else "failed"
    run.completed_at = timezone.now()
    run.result = f"Found {len(result.get('jobs', []))} jobs"
    run.result_data = result
    run.save()

    task.status = AgentTask.Status.COMPLETED if result["success"] else AgentTask.Status.FAILED
    task.last_run = timezone.now()
    task.run_count += 1
    task.last_result = f"Scraped {jobs_saved} jobs from {len(result.get('jobs', []))} found"
    task.last_error = "; ".join(result.get("errors", [])) if result.get("errors") else ""
    task.save()

    logger.info(f"Browser job scraping completed: saved {jobs_saved} jobs")

    return result


def extract_search_query(instructions: str) -> str:
    """Extract a search query from task instructions."""
    # Common patterns to look for
    keywords = []

    # Look for quoted terms
    import re
    quoted = re.findall(r'"([^"]+)"', instructions)
    keywords.extend(quoted)

    # Look for job-related keywords
    job_terms = [
        "software engineer", "developer", "engineer", "python", "javascript",
        "react", "backend", "frontend", "full stack", "ai", "ml", "data",
        "devops", "cloud", "aws", "remote"
    ]

    instructions_lower = instructions.lower()
    for term in job_terms:
        if term in instructions_lower:
            keywords.append(term)

    # Return first keyword or default
    return keywords[0] if keywords else "software engineer"


@shared_task
def scrape_linkedin_via_google(task_id: int, query: str = None):
    """
    Scrape LinkedIn jobs using Google Jobs API (Serper) to bypass bot detection.
    This is the recommended approach for LinkedIn since direct scraping is blocked.
    """
    from .models import AgentTask, TaskRun, TaskResult

    try:
        task = AgentTask.objects.select_related('workspace', 'workspace__owner').get(id=task_id)
    except AgentTask.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return {"success": False, "error": "Task not found"}

    # Check for Serper API key
    user = task.workspace.owner
    serper_key = (getattr(user, 'skill_api_keys', None) or {}).get('SERPER_API_KEY')

    if not serper_key:
        logger.warning("No SERPER_API_KEY configured - using fallback search")
        # Fallback to browser scraping of bot-friendly boards
        return scrape_jobs_with_browser_task(task_id, ["remoteok", "weworkremotely"], query)

    if not query:
        query = extract_search_query(task.instructions)

    logger.info(f"Searching LinkedIn jobs via Google Jobs API: {query}")

    # Create run record
    run = TaskRun.objects.create(task=task, status='running')
    task.status = AgentTask.Status.RUNNING
    task.save()

    try:
        # Use Serper Google Jobs API
        result = execute_serper_jobs(serper_key, query, "remote", 20)

        jobs = result.get("jobs", [])
        logger.info(f"Google Jobs API returned {len(jobs)} jobs")

        # Save results
        jobs_saved = 0
        for job in jobs:
            try:
                TaskResult.objects.create(
                    task=task,
                    run=run,
                    result_type="job",
                    title=job.get("title", ""),
                    url=job.get("link", ""),
                    data={
                        "company": job.get("company_name", ""),
                        "location": job.get("location", ""),
                        "source": job.get("via", "Google Jobs"),
                        "description": job.get("description", "")[:500],
                        "posted": job.get("detected_extensions", {}).get("posted_at", ""),
                    }
                )
                jobs_saved += 1
            except Exception as e:
                logger.error(f"Failed to save job: {e}")

        # Update task
        run.status = "completed"
        run.completed_at = timezone.now()
        run.result = f"Found {len(jobs)} jobs"
        run.result_data = {"jobs_count": len(jobs), "source": "google_jobs"}
        run.save()

        task.status = AgentTask.Status.COMPLETED
        task.last_run = timezone.now()
        task.run_count += 1
        task.last_result = f"Found {jobs_saved} jobs via Google Jobs API"
        task.save()

        return {"success": True, "jobs_count": jobs_saved}

    except Exception as e:
        logger.error(f"Google Jobs search failed: {e}")

        run.status = "failed"
        run.error_message = str(e)
        run.save()

        task.status = AgentTask.Status.FAILED
        task.last_error = str(e)
        task.save()

        return {"success": False, "error": str(e)}


# ============================================================================
# JobSpy Integration - FREE LinkedIn/Indeed/Glassdoor job scraping
# ============================================================================

JOBSPY_PLATFORMS = {
    'linkedin': {
        'name': 'LinkedIn',
        'reliable': False,
        'notes': 'Rate limited, use sparingly'
    },
    'indeed': {
        'name': 'Indeed',
        'reliable': True,
        'notes': 'Most reliable source'
    },
    'glassdoor': {
        'name': 'Glassdoor',
        'reliable': True,
        'notes': 'Includes salary and company reviews'
    },
    'zip_recruiter': {
        'name': 'ZipRecruiter',
        'reliable': True,
        'notes': 'US/Canada jobs'
    },
    'google': {
        'name': 'Google Jobs',
        'reliable': True,
        'notes': 'Aggregated listings'
    },
}


def scrape_jobs_with_jobspy(
    search_term: str,
    location: str = 'remote',
    sites: list = None,
    results_wanted: int = 20,
    hours_old: int = None,
    is_remote: bool = True,
    job_type: str = None,
    country: str = 'usa'
) -> dict:
    """
    Scrape jobs using JobSpy library.

    This is FREE and works with LinkedIn, Indeed, Glassdoor, ZipRecruiter, and Google Jobs
    without requiring API keys or login.

    Args:
        search_term: Job title/keywords to search
        location: Job location (e.g., 'San Francisco, CA' or 'remote')
        sites: List of sites to scrape (default: ['indeed', 'linkedin'])
        results_wanted: Number of results per site
        hours_old: Only jobs posted within X hours
        is_remote: Filter for remote jobs only
        job_type: 'fulltime', 'parttime', 'contract', 'internship'
        country: Country for Indeed searches

    Returns:
        dict with 'success', 'jobs', 'total', 'errors'
    """
    try:
        from jobspy import scrape_jobs
        import pandas as pd
    except ImportError:
        logger.error("JobSpy not installed. Run: pip install python-jobspy")
        return {
            'success': False,
            'jobs': [],
            'total': 0,
            'errors': ['JobSpy not installed']
        }

    if sites is None:
        sites = ['indeed', 'linkedin']

    logger.info(f"JobSpy search: '{search_term}' on {sites}, location={location}")

    try:
        # Build scrape parameters
        params = {
            'site_name': sites,
            'search_term': search_term,
            'location': location,
            'results_wanted': results_wanted,
            'country_indeed': country,
        }

        if hours_old:
            params['hours_old'] = hours_old

        if is_remote:
            params['is_remote'] = True

        if job_type:
            params['job_type'] = job_type

        # Scrape jobs
        jobs_df = scrape_jobs(**params)

        if jobs_df is None or len(jobs_df) == 0:
            return {
                'success': True,
                'jobs': [],
                'total': 0,
                'errors': []
            }

        # Convert DataFrame to list of dicts
        jobs = []
        for _, row in jobs_df.iterrows():
            job = {
                'title': str(row.get('title', '')) if pd.notna(row.get('title')) else '',
                'company': str(row.get('company', '')) if pd.notna(row.get('company')) else '',
                'location': str(row.get('location', '')) if pd.notna(row.get('location')) else '',
                'job_url': str(row.get('job_url', '')) if pd.notna(row.get('job_url')) else '',
                'job_type': str(row.get('job_type', '')) if pd.notna(row.get('job_type')) else '',
                'date_posted': str(row.get('date_posted', '')) if pd.notna(row.get('date_posted')) else '',
                'is_remote': bool(row.get('is_remote', False)),
                'source': str(row.get('site', '')) if pd.notna(row.get('site')) else '',
            }

            # Add salary if available
            if pd.notna(row.get('min_amount')):
                job['salary_min'] = float(row['min_amount'])
            if pd.notna(row.get('max_amount')):
                job['salary_max'] = float(row['max_amount'])
            if pd.notna(row.get('interval')):
                job['salary_interval'] = str(row['interval'])

            # Add description snippet if available
            if pd.notna(row.get('description')):
                job['description'] = str(row['description'])[:500]

            jobs.append(job)

        logger.info(f"JobSpy found {len(jobs)} jobs")

        return {
            'success': True,
            'jobs': jobs,
            'total': len(jobs),
            'errors': []
        }

    except Exception as e:
        logger.error(f"JobSpy scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'jobs': [],
            'total': 0,
            'errors': [str(e)]
        }


@shared_task
def scrape_jobs_with_jobspy_task(
    task_id: int,
    sites: list = None,
    query: str = None,
    location: str = 'remote',
    results_wanted: int = 25,
    hours_old: int = None,
    is_remote: bool = True
):
    """
    Celery task to scrape jobs using JobSpy.

    This is the recommended approach for scraping LinkedIn/Indeed/Glassdoor
    as it's FREE and handles bot detection automatically.

    Args:
        task_id: AgentTask ID
        sites: List of job sites ['indeed', 'linkedin', 'glassdoor', 'zip_recruiter', 'google']
        query: Search query (extracted from task if not provided)
        location: Job location
        results_wanted: Number of results
        hours_old: Only jobs posted within X hours
        is_remote: Filter for remote jobs
    """
    from .models import AgentTask, TaskRun, TaskResult

    try:
        task = AgentTask.objects.select_related('workspace', 'workspace__owner').get(id=task_id)
    except AgentTask.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return {"success": False, "error": "Task not found"}

    # Create run record
    run = TaskRun.objects.create(task=task, status='running')
    task.status = AgentTask.Status.RUNNING
    task.save()

    # Extract search query from task instructions if not provided
    if not query:
        query = extract_search_query(task.instructions)

    # Default sites if none specified
    if not sites:
        sites = ['indeed', 'linkedin']

    logger.info(f"Starting JobSpy scraping: query='{query}', sites={sites}, location={location}")

    try:
        # Scrape jobs using JobSpy
        result = scrape_jobs_with_jobspy(
            search_term=query,
            location=location,
            sites=sites,
            results_wanted=results_wanted,
            hours_old=hours_old,
            is_remote=is_remote
        )

        jobs = result.get('jobs', [])
        logger.info(f"JobSpy returned {len(jobs)} jobs")

        # Save results to database
        jobs_saved = 0
        for job in jobs:
            try:
                # Build salary string if available
                salary = ""
                if job.get('salary_min') and job.get('salary_max'):
                    interval = job.get('salary_interval', 'yearly')
                    salary = f"${job['salary_min']:,.0f} - ${job['salary_max']:,.0f} {interval}"
                elif job.get('salary_min'):
                    salary = f"${job['salary_min']:,.0f}+"

                TaskResult.objects.create(
                    task=task,
                    run=run,
                    result_type="job",
                    title=job.get('title', 'Untitled'),
                    url=job.get('job_url', ''),
                    data={
                        'company': job.get('company', ''),
                        'location': job.get('location', ''),
                        'salary': salary,
                        'job_type': job.get('job_type', ''),
                        'is_remote': job.get('is_remote', False),
                        'source': job.get('source', ''),
                        'date_posted': job.get('date_posted', ''),
                        'description': job.get('description', '')[:300] if job.get('description') else '',
                    }
                )
                jobs_saved += 1
            except Exception as e:
                logger.error(f"Failed to save job result: {e}")

        # Update run
        run.status = "completed" if result['success'] else "failed"
        run.completed_at = timezone.now()
        run.result = f"Found {len(jobs)} jobs from {', '.join(sites)}"
        run.result_data = {
            'jobs_count': len(jobs),
            'jobs_saved': jobs_saved,
            'sites': sites,
            'query': query,
            'errors': result.get('errors', [])
        }
        run.save()

        # Update task
        task.status = AgentTask.Status.COMPLETED if result['success'] else AgentTask.Status.FAILED
        task.last_run = timezone.now()
        task.run_count += 1
        task.last_result = f"Found {jobs_saved} jobs via JobSpy ({', '.join(sites)})"
        task.last_error = "; ".join(result.get('errors', [])) if result.get('errors') else ""
        task.save()

        logger.info(f"JobSpy scraping completed: saved {jobs_saved} jobs")

        return {
            'success': result['success'],
            'jobs_count': len(jobs),
            'jobs_saved': jobs_saved,
            'sites': sites,
            'errors': result.get('errors', [])
        }

    except Exception as e:
        logger.error(f"JobSpy task failed: {e}")
        import traceback
        traceback.print_exc()

        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = timezone.now()
        run.save()

        task.status = AgentTask.Status.FAILED
        task.last_error = str(e)
        task.save()

        return {"success": False, "error": str(e)}


@shared_task
def smart_job_search_task(task_id: int, query: str = None, location: str = 'remote'):
    """
    Smart job search that automatically selects the best method:
    1. Uses JobSpy for LinkedIn/Indeed (FREE, no API keys)
    2. Falls back to browser scraping for other sites

    This is the recommended entry point for job searching.
    """
    from .models import AgentTask

    try:
        task = AgentTask.objects.get(id=task_id)
    except AgentTask.DoesNotExist:
        return {"success": False, "error": "Task not found"}

    if not query:
        query = extract_search_query(task.instructions)

    logger.info(f"Smart job search: '{query}' in '{location}'")

    # Use JobSpy for the main job boards (LinkedIn, Indeed, Glassdoor)
    # This is FREE and handles bot detection
    return scrape_jobs_with_jobspy_task(
        task_id=task_id,
        sites=['indeed', 'linkedin', 'glassdoor'],
        query=query,
        location=location,
        results_wanted=30,
        is_remote=(location.lower() == 'remote')
    )
