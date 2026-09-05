# Resonant

Resonant is a secure AI job-finding assistant for a resume-worthy portfolio project. Users upload a resume, search for target roles, receive ranked job matches with fit scores and skill gaps, and can delete application data when finished.

## High-Level Architecture
- Next.js frontend in `apps/web`.
- FastAPI backend in `apps/api`.
- LangGraph agent workflow for resume-to-job matching.
- Local TF-IDF semantic ranking blended with deterministic skill-overlap scoring.
- Supabase Auth/Postgres with RLS.
- DeepEval and Promptfoo for AI evaluation and red-team checks.
- Helicone and Amplitude for monitoring and analytics.

## Tech Stack
- TypeScript, Next.js, React.
- Python, FastAPI, Pydantic, LangGraph.
- Supabase Auth/Postgres.
- LiteLLM-compatible model routing.
- DeepEval, Promptfoo, Pytest, Playwright.

## Repository Structure
```text
apps/
  web/       Next.js frontend
  api/       FastAPI backend
packages/
  shared/    Shared TypeScript contracts
supabase/    SQL migrations and RLS policies
evals/       DeepEval and Promptfoo suites
examples/    Safe sample resumes for demos and red-team walkthroughs
tests/       Deterministic tests
scripts/     Security and setup helpers
```

## Local Setup
```bash
npm install
python3 -m venv apps/api/.venv
apps/api/.venv/bin/pip install -e 'apps/api[dev]'
cp .env.example .env
```

## Environment Configuration
Copy `.env.example` and fill in real values locally or in Vercel/Render dashboards. Never commit `.env`.
The API loads env values from `.env`, `apps/.env`, and `apps/api/.env` in that order, with later
files overriding earlier ones. Keep backend-only secrets out of `apps/web/.env.local`; the web app
should only use `NEXT_PUBLIC_*` values.

## Run The Application
```bash
npm run dev:web
npm run dev:api
```

Or run both services through Docker Compose:
```bash
docker compose up --build
```

The compose stack starts the API on `http://localhost:8000` and the web app on
`http://localhost:3000`.

With `DEMO_AUTH=true` in local development, authentication works without Supabase. AI analysis
still requires a configured model provider. Set `ALLOW_DEMO_DATA=true` only for explicitly labeled
curated job fixtures. Production rejects demo authentication at startup.
Backend npm scripts use `scripts/api_python.py`, which selects `apps/api/.venv/bin/python`
locally and falls back to the active Python interpreter in CI.

For live job data, configure either Adzuna (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) or the
Apify MyCareersFuture actor (`APIFY_MCF_RUN_URL`, `APIFY_API_TOKEN`). Adzuna is used first
when both are present; Apify is the secondary real-data source.

For live AI, set `OPENAI_API_KEY` and `CHEAP_MODEL` in Render. Leave `STRONG_MODEL` blank
for the lowest-cost route; if configured, it is used only as a fallback for match and rank
tasks after the cheap model fails. If no model is configured, the API and UI report
the failed AI stage and generate no synthetic recommendations.

For production persistence, generate a backend-only app encryption key:
```bash
apps/api/.venv/bin/python scripts/generate_encryption_key.py
```

Set the generated value as `APP_ENCRYPTION_KEY` in Render only.

## Run Tests
```bash
npm run test
npm run test:api
npm run security:scan
npm run eval:promptfoo
npm run eval:deepeval
```

The required DeepEval and Promptfoo release gates run without provider keys or paid services.
Configured providers add live extraction, normalization, reasoning, and ranking paths on top of those gates.

## Important Development Commands
```bash
npm run lint
npm run typecheck
npm run audit
npm run repo:hygiene
npm run hooks:install      # optional local pre-commit guard for first push
npm run deploy:check        # validates the template and frontend secret boundaries
npm run deploy:check:prod
npm run smoke:demo -- --api http://127.0.0.1:8000
```

## Security
Read `SECURITY_CHECKLIST.md` before adding features. The project is designed around server-side auth, Supabase RLS, app-layer encryption, validation, response trimming, upload restrictions, rate limits, secret scanning, and free-tier-safe deployment.

## Portfolio Positioning
Use [PORTFOLIO_BRIEF.md](/Users/jeffrey/Desktop/projects/job/PORTFOLIO_BRIEF.md) for resume bullets, an interview pitch, demo flow, and technical proof points.

Use [DESIGN.md](/Users/jeffrey/Desktop/projects/job/DESIGN.md) for product taste, UI rules, and demo-facing design constraints.

Use [DEMO_GUIDE.md](/Users/jeffrey/Desktop/projects/job/DEMO_GUIDE.md) plus the sample resumes in `examples/` for recruiter walkthroughs and red-team demonstrations.

## Deployment
Use [DEPLOYMENT_RUNBOOK.md](/Users/jeffrey/Desktop/projects/job/DEPLOYMENT_RUNBOOK.md) when moving from local MVP to Supabase, Render, and Vercel.
