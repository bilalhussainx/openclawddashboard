# OpenClaw Dashboard

**Build, deploy, and manage autonomous AI agents — with automated job application built in.**

OpenClaw Dashboard is a full-stack platform for creating AI agents that do real work: web research, job hunting, code execution, recipe finding, travel planning, and more. Results are delivered via Telegram, Slack, Discord, or the dashboard UI.

The **Job Auto-Apply** module takes this further — it discovers jobs across 5 boards (LinkedIn, Indeed, Glassdoor, HN Who's Hiring, RemoteOK), scores them against your profile, generates cover letters with Claude AI, and submits applications via Playwright browser automation on company career pages (Greenhouse, Lever, Workday, Ashby, etc.).

---

## Demo Video

<!-- Replace the placeholder below with your Loom video link -->

[![Watch the Demo](https://img.shields.io/badge/Loom-Watch_Demo-blue?style=for-the-badge&logo=loom)](YOUR_LOOM_VIDEO_URL_HERE)

> **Paste your Loom link above** to showcase:
> - Dashboard walkthrough and workspace creation
> - Job search running across 5 boards with AI scoring
> - Playwright automating a Greenhouse application end-to-end
> - Telegram notifications with job results
> - Startup Jobs page with AI badge detection

---

## What It Actually Does

### AI Agent Workspaces

You create a **workspace** (an isolated agent environment), give it instructions, install skills from 1,662 available in the marketplace, connect a messaging channel, and let it work.

```
You: "Find AI Engineer jobs on LinkedIn, score them, notify me on Telegram"
Agent: Scrapes LinkedIn via JobSpy → Scores 84 jobs → Sends top 10 to Telegram
```

```
You: "Plan a 5-day Tokyo trip for a tech/anime/food enthusiast"
Agent: Searches travel sites → Builds itinerary → Saves 3 structured guides with scores
```

### Job Auto-Apply (JobApply Module)

The killer feature — an end-to-end automated job application pipeline:

1. **Discover** — Scrapes LinkedIn, Indeed, Glassdoor (via JobSpy), HN Who's Hiring (Algolia + Firebase API), and RemoteOK (JSON API)
2. **Score** — AI scores each job 0-100 against your resume, skills, and preferences
3. **Generate** — Claude AI writes a tailored cover letter per application
4. **Apply** — Playwright browser automation fills career page forms, uploads your resume, and submits

```
656 jobs discovered → 9 applications submitted → Anthropic Greenhouse form filled + submitted automatically
```

---

## Built on OpenClaw, Lobster & ClawdBot

This project is a **management dashboard built on top of the OpenClaw/ClawdBot/Lobster ecosystem** — the AI agent framework and workflow tools developed around Anthropic's Claude.

### OpenClaw — The Agent Framework

**[OpenClaw](https://github.com/anthropics/openclaw)** is the open-source AI agent framework at the core of this dashboard. Each workspace spins up a dedicated OpenClaw Docker container (`openclaw/openclaw:latest`) with:

- **Gateway API** — WebSocket server on a per-workspace port (`19000 + workspace_id`) for sending messages and receiving agent responses
- **Tool-use agent loop** — Claude/GPT calls tools (web_search, scrape_webpage, save_result, send_message) and the framework executes them
- **Browser automation** — Built-in CDP bridge for navigating pages, taking accessibility tree snapshots, and interacting with form elements
- **Channel delivery** — Native Telegram, Slack, and Discord integration via bot tokens configured per workspace

The dashboard generates OpenClaw configuration for each workspace:
```
.openclaw/
├── openclaw.json          # Agent model, channels, gateway settings
├── workspace/
│   ├── SOUL.md            # Agent personality and system prompt
│   └── skills/            # Installed skill files from ClawHub
├── credentials/           # Channel tokens (telegram.json, slack.json)
└── .env                   # API keys (ANTHROPIC_API_KEY, etc.)
```

### ClawdBot — The Tool Endpoint Platform

**ClawdBot** is the tool/skill ecosystem that OpenClaw agents use. The dashboard integrates with it through:

- **ClawHub** — Skill marketplace with 1,662 installable skills (`skills/clawhub_sync.py` syncs them)
- **ClawdBot skills** — Skills like `clawdbot-filesystem` (file operations), `claw-shell` (shell commands), `job-search-mcp` (job board scraping) are installed into workspaces and injected into the agent's system prompt
- **Tool endpoints** — ClawdBot exposes tools at `{CLAWD_URL}/tools/invoke` that agents and Lobster workflows can call

### Lobster — The Workflow Engine

**[Lobster](https://github.com/clawdbot/lobster)** (`@clawdbot/lobster`) is a Moltbot-native workflow orchestration engine that provides:

- **Typed JSON pipelines** — Composable workflows that pipe structured data (not text), enabling deterministic multi-step automation
- **`clawd.invoke`** — Command that calls ClawdBot tool endpoints, allowing workflows to use any installed skill
- **Approval gates** — Human-in-the-loop checkpoints for workflows that need review before proceeding
- **Token efficiency** — Pre-composed workflows save tokens vs. having the AI construct queries each time

Lobster's approach to browser automation, ATS detection, and form field mapping directly influenced the JobApply module's Playwright implementation. Our `playwright_apply.py` builds on concepts from Lobster's CDP-based approach but diverges with:
- Direct Playwright control (vs. CDP snapshots) for more reliable form filling
- Keyword-priority dropdown matching for Greenhouse custom fields
- Validation error retry logic
- 15+ ATS detection patterns

### How They Work Together

```
┌─────────────────────────────────────────────────────────┐
│            OpenClaw Dashboard (this repo)                │
│                 Django + Next.js                         │
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Per-Workspace OpenClaw Container                  │ │
│  │  • Claude/GPT agent with tool-use loop             │ │
│  │  • Gateway WebSocket API (port 19000+id)           │ │
│  │  • ClawdBot skills injected into system prompt     │ │
│  │  • Channels: Telegram / Slack / Discord            │ │
│  └────────────────────────────────────────────────────┘ │
│                          │                              │
│                  Gateway API calls                      │
│                          │                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Lobster Workflow Engine (optional)                 │ │
│  │  • clawd.invoke → ClawdBot tool endpoints          │ │
│  │  • Deterministic pipelines (token-efficient)       │ │
│  │  • Approval gates for human review                 │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │  JobApply Module (Celery workers)                  │ │
│  │  • OpenClaw Gateway mode (apply_automation.py)     │ │
│  │    → Browser snapshots + accessibility tree        │ │
│  │  • Direct Playwright mode (playwright_apply.py)    │ │
│  │    → Headless Chromium for career page forms       │ │
│  │  • Informed by Lobster's ATS detection patterns    │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   FRONTEND                        │
│         Next.js 14 + TypeScript + Tailwind        │
│              localhost:3000                        │
└──────────────────────┬───────────────────────────┘
                       │  REST API (JWT Auth)
┌──────────────────────▼───────────────────────────┐
│                   BACKEND                         │
│         Django 5 + DRF + PostgreSQL               │
│              localhost:8000                        │
├──────────┬───────────────────────┬───────────────┤
│  Celery  │    Celery Beat        │   Playwright  │
│  Worker  │    (Scheduler)        │   (Browser)   │
└──────────┴───────────────────────┴───────────────┘
     │              │                      │
     ▼              ▼                      ▼
 Claude/GPT    Scheduled Jobs       Career Page
 API Calls     Discovery & Apply    Form Automation
     │
     ▼
 OpenClaw Containers (per workspace)
  └── Agent execution + Browser + Channels
```

**Services (Docker Compose):**
| Service | Purpose |
|---------|---------|
| `backend` | Django API server |
| `celery` | Task worker (job discovery, cover letters, Playwright apply) |
| `celery-beat` | Scheduled task runner |
| `frontend` | Next.js dashboard UI |
| `db` | PostgreSQL 16 |
| `redis` | Celery broker + cache |
| `nginx` | Reverse proxy |

---

## Job Auto-Apply — Deep Dive

### How It Works

```
User configures preferences (keywords, location, boards, min score)
         │
         ▼
Celery Beat triggers discover_jobs() on schedule (or on-demand)
         │
         ├── JobSpy scrapes LinkedIn, Indeed, Glassdoor
         ├── Algolia + Firebase API scrapes HN Who's Hiring
         └── RemoteOK JSON API fetches remote startup jobs
         │
         ▼
AI Scoring Engine scores each job 0-100
  • Keyword match (title + description)
  • Location/remote compatibility
  • Salary range fit
  • Skills overlap with resume
         │
         ▼
User reviews scored listings in dashboard
  • Filter by source, min score, time window
  • AI badge highlights jobs mentioning AI/LLM/Claude
  • One-click Apply or Dismiss
         │
         ▼
Click "Apply" triggers Celery pipeline:
  1. Generate cover letter (Claude API or local Ollama)
  2. Playwright opens job URL
  3. If LinkedIn/Indeed → follows "Apply on company site" link
  4. Detects ATS (Greenhouse, Lever, Workday, Ashby, etc.)
  5. Fills form fields (name, email, phone, resume upload)
  6. Fills custom fields (country, visa, relocation, authorization)
  7. Submits application
  8. Records automation log with every step
```

### Playwright Automation Details

The browser automation (`playwright_apply.py`) handles the full complexity of real-world career pages:

**ATS Detection** — Identifies 15+ applicant tracking systems by URL pattern:
- Greenhouse (`boards.greenhouse.io`, `grnh.se`)
- Lever (`jobs.lever.co`)
- Workday (`myworkdayjobs.com`)
- Ashby (`ashbyhq.com`)
- SmartRecruiters, BambooHR, iCIMS, Jobvite, Recruitee, Breezy, Dover, Rippling

**Job Board → Career Page Redirect:**
- LinkedIn/Indeed URLs → clicks "Apply on company site" link → follows to career page
- RemoteOK → searches for "Careers Site" link in expanded job section → falls back to company website
- Generic → navigates directly

**Greenhouse Form Automation (Most Complex):**
- Detects and fills basic fields (first name, last name, email, phone)
- Handles custom `select__input` dropdown widgets (not standard HTML selects)
  - Clicks to open → types to filter → selects matching option
- Fills custom required fields with keyword-priority matching:
  - Visa sponsorship → "No"
  - Authorization to work → "I am authorized to work in the country due to my nationality"
  - Country → "Canada"
  - Relocation → "Yes"
  - How did you hear about us → "Job board"
  - Interviewed before → "No"
- Uploads resume PDF via file input
- Submits and detects:
  - Success confirmation pages
  - Validation errors (retries with default values)
  - Security code verification (Greenhouse email verification)

**Anti-Detection:**
- Human-like random delays between actions (0.3–2.0s)
- Realistic browser fingerprint (viewport, user-agent)
- `--disable-blink-features=AutomationControlled`

### Startup Scrapers

Two custom scrapers for AI/startup jobs:

**HN Who's Hiring** (`startup_scrapers.py`):
- Algolia API finds the latest "Ask HN: Who is hiring?" thread
- Firebase API fetches top 200 comment IDs in parallel (ThreadPoolExecutor)
- Parses pipe-delimited comment text: `Company | Location | Title | URL`
- 10-minute response cache

**RemoteOK** (`startup_scrapers.py`):
- Single GET to `https://remoteok.io/api` (free, no auth)
- Client-side keyword filtering
- 10-minute response cache

### Data Model

| Model | Purpose |
|-------|---------|
| `Resume` | Uploaded PDF/DOCX with Claude-parsed structured data (name, email, skills, experience) |
| `JobPreferences` | Search keywords, location, boards, auto-apply settings, salary range |
| `JobListing` | Discovered job with match score, keywords, source board, dedup hash |
| `JobApplication` | Full lifecycle: queued → generating_cover → applying → applied/failed |
| `DailyApplicationSummary` | Daily stats for notification digest |

### Current Stats (Live System)

- **656** non-dismissed job listings across 5 boards
- **9** applications submitted (Anthropic via Greenhouse = success)
- **5** job boards: LinkedIn, Indeed, Glassdoor, HN Hiring, RemoteOK
- **15+** ATS systems detected and handled

---

## Dashboard Features

### Agent Workspaces
- Create isolated agent environments with custom instructions
- Choose AI model (Claude Sonnet 4, Claude Opus, GPT-4)
- Configure system prompt, personality, knowledge base
- Deploy/stop/restart with one click
- Install skills from 1,662-skill marketplace

### Task Automation
- Natural language task instructions
- On-demand or scheduled execution
- Agent uses tools autonomously: web_search, scrape, save_result, send_message
- Universal results UI (jobs, articles, code, recipes, facts)

### Multi-Channel Notifications
| Channel | Status |
|---------|--------|
| Telegram | Working — Bot sends results via Bot API |
| Slack | Working — Bot posts to channels/DMs |
| Discord | Working — Bot sends messages to servers |
| Dashboard | Working — View all results in web UI |

### Job Apply Pages
| Page | Description |
|------|-------------|
| `/dashboard/jobapply` | Dashboard with stats, recent listings, applications |
| `/dashboard/jobapply/listings` | All jobs with source/score filters, apply/dismiss |
| `/dashboard/jobapply/startups` | HN + RemoteOK jobs with AI badge, time filter |
| `/dashboard/jobapply/applications` | Application status tracking |
| `/dashboard/jobapply/resumes` | Upload and manage resumes |
| `/dashboard/jobapply/preferences` | Configure keywords, boards, auto-apply |

### Additional Features
- JWT authentication with token refresh
- Knowledge base per workspace
- Stripe billing (Free / Pro / Enterprise)
- Analytics dashboard
- Dark mode UI

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Radix UI, React Query, Zustand |
| Backend | Django 5, Django REST Framework, Celery, Celery Beat |
| Database | PostgreSQL 16 |
| Cache/Broker | Redis 7 |
| Browser Automation | Playwright (Chromium, headless) |
| AI Models | Anthropic Claude API, OpenAI GPT, Ollama (local) |
| Agent Framework | OpenClaw (Anthropic's open-source agent framework) |
| Job Scraping | JobSpy (LinkedIn/Indeed/Glassdoor), custom scrapers (HN/RemoteOK) |
| Payments | Stripe |
| Containerization | Docker, Docker Compose |
| Proxy | Nginx |

---

## Project Structure

```
openclawddashboard/
├── backend/
│   ├── config/              # Django settings, URLs, Celery config
│   ├── core/                # User model, JWT auth, profile
│   ├── workspaces/          # Workspace CRUD, deployment, agent execution
│   ├── automations/         # Agent tasks, tool execution engine, results
│   ├── skills/              # Skill marketplace, ClawHub sync (1,662 skills)
│   ├── billing/             # Stripe subscriptions, usage tracking
│   ├── jobapply/            # ⭐ Job Auto-Apply module
│   │   ├── models.py        # Resume, JobPreferences, JobListing, JobApplication
│   │   ├── views.py         # REST API endpoints with pagination
│   │   ├── serializers.py   # DRF serializers with application_info
│   │   ├── tasks.py         # Celery tasks: discover_jobs, process_application
│   │   ├── scoring.py       # AI match scoring engine
│   │   ├── cover_letter.py  # Claude/Ollama cover letter generation
│   │   ├── playwright_apply.py  # ⭐ Direct Playwright automation (Greenhouse, Lever, etc.)
│   │   ├── apply_automation.py  # ⭐ OpenClaw Gateway browser automation
│   │   ├── startup_scrapers.py  # HN Who's Hiring + RemoteOK scrapers
│   │   └── resume_parser.py     # Claude-powered resume parsing
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/
│   ├── src/app/
│   │   ├── dashboard/
│   │   │   ├── jobapply/         # ⭐ Job Apply pages
│   │   │   │   ├── page.tsx      # Dashboard with stats
│   │   │   │   ├── listings/     # All job listings
│   │   │   │   ├── startups/     # HN + RemoteOK startup jobs
│   │   │   │   ├── applications/ # Application tracking
│   │   │   │   ├── resumes/      # Resume management
│   │   │   │   └── preferences/  # Search configuration
│   │   │   ├── workspaces/       # Agent workspace management
│   │   │   ├── skills/           # Skills marketplace
│   │   │   ├── settings/         # API keys, profile
│   │   │   ├── analytics/        # Usage metrics
│   │   │   └── channels/         # Messaging channels
│   │   ├── login/
│   │   ├── register/
│   │   └── onboarding/
│   ├── src/lib/api.ts       # Axios API client with JWT interceptors
│   ├── src/components/      # Reusable UI components (shadcn/ui)
│   └── src/stores/          # Zustand state stores
│
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
│
├── WORKING_AGENTS_GUIDE.md  # Detailed agent testing documentation
└── README.md                # This file
```

---

## Setup

### Prerequisites
- Docker and Docker Compose
- Anthropic API key (or OpenAI API key)
- (Optional) Telegram Bot Token from @BotFather

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/openclawddashboard.git
cd openclawddashboard
cp .env.example .env
```

Edit `.env`:
```env
DJANGO_SECRET_KEY=your-secret-key
DB_PASSWORD=your-secure-db-password
```

### 2. Build and start

```bash
cd docker
docker-compose up -d --build
```

### 3. Run migrations

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

### 4. Sync skills marketplace

```bash
docker-compose exec backend python manage.py shell -c "
from skills.clawhub_sync import sync_clawhub_skills
stats = sync_clawhub_skills()
print(stats)
"
```

### 5. Open the dashboard

Navigate to `http://localhost:3000`, register, add your API key in Settings, and start using it.

### 6. Set up Job Auto-Apply

1. Go to **Settings** → add your Anthropic API key
2. Go to **Job Apply → Resumes** → upload your resume PDF
3. Go to **Job Apply → Preferences** → set keywords, location, enable boards
4. Click **Search Now** to discover jobs
5. Review scored listings and click **Apply** on any job

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register |
| POST | `/api/auth/login/` | Login (JWT) |
| POST | `/api/auth/refresh/` | Refresh token |
| GET | `/api/auth/me/` | Current user |

### Job Auto-Apply
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobapply/dashboard/` | Stats overview |
| GET/POST | `/api/jobapply/resumes/` | Resume CRUD |
| POST | `/api/jobapply/resumes/{id}/parse/` | AI parse resume |
| GET/PATCH | `/api/jobapply/preferences/` | Search preferences |
| GET | `/api/jobapply/listings/` | Browse scored listings |
| POST | `/api/jobapply/listings/search_now/` | Trigger job search |
| POST | `/api/jobapply/listings/search_startups/` | Search HN + RemoteOK |
| POST | `/api/jobapply/listings/{id}/apply/` | Submit application |
| POST | `/api/jobapply/listings/{id}/dismiss/` | Dismiss listing |
| GET | `/api/jobapply/applications/` | Application history |
| POST | `/api/jobapply/applications/{id}/retry/` | Retry failed apply |

### Workspaces & Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/workspaces/` | List / Create |
| POST | `/api/workspaces/{id}/deploy/` | Deploy agent |
| POST | `/api/workspaces/{id}/tasks/{taskId}/run/` | Run task |
| GET | `/api/workspaces/{id}/tasks/{taskId}/results/` | Get results |

### Skills
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/skills/` | Browse 1,662 skills |
| POST | `/api/skills/{slug}/install/` | Install to workspace |

---

## Tested Capabilities

**19 agent tasks tested (Feb 2026):**

| Task | Results | Status |
|------|---------|--------|
| LinkedIn Job Search | 84 jobs scored | Working |
| Indeed + LinkedIn AI Jobs | 46 jobs | Working |
| HN Who's Hiring scrape | Jobs with AI badges | Working |
| RemoteOK scrape | Remote startup jobs | Working |
| Greenhouse auto-apply | Anthropic application submitted | Working |
| DuckDuckGo Search | 2-3 articles | Working |
| Code Execution (Fibonacci) | 1 result | Working |
| Tokyo 5-Day Trip Planner | 3 guides | Working |
| AI Startup Research | 5 profiles | Working |
| Weekly Meal Prep Recipes | 5 recipes | Working |
| Telegram Notifications | Results sent to bot | Working |

**15 of 19 tasks completed successfully (79% success rate)**

---

## Workflow Screenshots

<!-- Add screenshots of your dashboard here -->

| Screen | Description |
|--------|-------------|
| ![Dashboard](screenshots/dashboard.png) | Main job apply dashboard with stats |
| ![Listings](screenshots/listings.png) | Scored job listings with source filters |
| ![Startups](screenshots/startups.png) | Startup jobs with AI badges |
| ![Apply](screenshots/apply.png) | Application status and automation log |

> Replace with actual screenshots or Loom video frames.

---

## License

MIT

---

Built with Django, Next.js, Claude, Playwright, and a lot of automated job applications.
