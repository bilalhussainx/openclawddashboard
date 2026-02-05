# Cover Letter — OpenClaw / Moltbot AI Agent Engineer

---

Hi,

I'm Bilal Hussain, a full-stack developer based in Toronto. I've spent the last several weeks building a production AI agent dashboard on top of OpenClaw — the exact framework your project uses — and I'd like to bring that hands-on experience to this role.

## What I've Built

**OpenClaw Dashboard** (https://github.com/bilalhussainx/openclawddashboard) — a full-stack platform for deploying and managing autonomous AI agents, with a complete automated job application pipeline:

- **Django 5 backend** with 8 apps, Celery task queue, and Celery Beat scheduler
- **Next.js 14 frontend** with 23 pages, dark mode, shadcn/ui components
- **OpenClaw integration** — each workspace spins up an OpenClaw Docker container with Gateway API for agent execution, browser automation, and channel delivery
- **Job Auto-Apply module** — discovers jobs across 5 boards (LinkedIn, Indeed, Glassdoor, HN Who's Hiring, RemoteOK), scores them with AI, generates cover letters with Claude, and submits applications via **Playwright browser automation** on career pages (Greenhouse, Lever, Workday, Ashby — 15+ ATS systems detected)
- **Telegram notifications** — tested and working, agents send results directly to Telegram bots
- **1,662 skills marketplace** synced from ClawHub

The Playwright automation alone handles: ATS detection by URL pattern, Greenhouse custom dropdown widgets (`select__input` → click → type → select), keyword-priority field matching (visa, authorization, relocation, country), resume PDF upload, validation error retry, and security code detection. I successfully automated an application to Anthropic's own Greenhouse form — received the security code email confirming submission.

## Why Me

I would love to build with you OpenClaw into the reliable executive AI assistant you want. I already have channels with Telegram tested in my app that runs certain agents I have created in the Dashboard for OpenClaw that I am designing. I was using it to scrape and suggest jobs relevant to AI-Native Workflow with preference of Claude Code for development and efficiency. I build features in hours not days and know how to thoroughly test the code using test cases, e2e and integration tests and validate the code before committing it. You can trust me to make your project my main goal for the next 6 months and more.

## Technical Fit

- **OpenClaw** — I've built an entire dashboard layer on top of it. I know the Gateway API, container orchestration, config generation, and tool-use agent loops.
- **Claude API** — Used extensively for cover letter generation, resume parsing, job scoring, and agent task execution. I work with Claude Code daily as my primary development tool.
- **Playwright** — Built production browser automation for career page form filling inside Docker containers (headless Chromium, anti-detection, human-like delays).
- **Django + Celery + PostgreSQL** — The backend stack I've been shipping with for this project. Background job discovery, scheduled tasks, retry logic.
- **Next.js + TypeScript + React Query** — 23-page frontend with JWT auth, real-time query invalidation, Zustand state management.
- **Docker Compose** — 7-service deployment (backend, celery, celery-beat, frontend, postgres, redis, nginx).

## Availability

I'm available to start immediately and can commit full-time to this project. I'm based in Toronto (EST) and flexible on working hours.

Looking forward to discussing how I can help build Moltbot into the agent you envision.

Best,
Bilal Hussain
bilalhussain.v1@gmail.com
GitHub: https://github.com/bilalhussainx/openclawddashboard
