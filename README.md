# Resonant

**An AI job-search assistant that turns your resume into ranked job matches, fit scores, and skill-gap insights.**

> **Status: no longer deployed.** Resonant used to run live on Vercel, Render, and Supabase. I took it
> down to stop paying for hosting and LLM API usage. The code is still here, and you can run it
> locally by following the steps below.

---

## What It Does

1. **Upload a resume.** Resonant parses it and pulls out your skills, experience, and seniority.
2. **Search for a role.** For example, `AI Engineer` in `Singapore`. It fetches live postings from job APIs.
3. **Get ranked matches.** Each job gets a fit score, the skills you match, the skills you're missing,
   and a short explanation of the fit.
4. **Save jobs and give feedback.** Bookmark good matches and rate how useful each recommendation was.
5. **Delete your data.** One click removes everything you uploaded.

## How It Works

The matching pipeline is a LangGraph agent:

```text
parse_resume → analyze_resume → fetch_jobs → analyze_jobs → select_candidates
             → reason_matches → synthesize_ranking → validate_output → persist_results
```

- **Hybrid ranking.** LLM reasoning is combined with local TF-IDF semantic similarity and a
  deterministic skill-overlap score, so rankings don't depend only on what the model says.
- **Model output is untrusted.** Every LLM response is checked against a schema before it's used.
  When a stage fails, the UI shows the failure instead of inventing recommendations.
- **Cost-aware routing.** A cheap model handles most tasks, and a stronger model is used only as a
  fallback. Caching and daily limits keep API spend bounded.
- **Security first.** Server-side auth, Supabase row-level security, app-layer encryption, strict
  upload validation, rate limits, and secret scanning.
- **Evaluated.** DeepEval tests check groundedness and ranking quality, and Promptfoo red-team cases
  check prompt injection and malformed output.

## Tech Stack

| Layer      | Tools                                               |
| ---------- | --------------------------------------------------- |
| Frontend   | Next.js, React, TypeScript                          |
| Backend    | Python, FastAPI, Pydantic, LangGraph                |
| AI         | LiteLLM-compatible model routing, TF-IDF ranking    |
| Data/Auth  | Supabase Postgres + Auth with RLS                   |
| Testing    | Pytest, Playwright, DeepEval, Promptfoo             |
| Monitoring | Helicone, Amplitude                                 |

## Repository Structure

```text
apps/
  web/       Next.js frontend
  api/       FastAPI backend and LangGraph agent
packages/
  shared/    Shared TypeScript contracts
supabase/    SQL migrations and RLS policies
evals/       DeepEval and Promptfoo suites
examples/    Sample resumes (including a prompt-injection test case)
tests/       API and security tests
scripts/     Setup and security helpers
```

## Running It Locally

Requirements: Node 20+ and Python 3.11+.

```bash
npm install
python3 -m venv apps/api/.venv
apps/api/.venv/bin/pip install -e 'apps/api[dev]'
cp .env.example .env
```

In `.env`, set:

- `DEMO_AUTH=true` to skip Supabase sign-in during local development.
- `OPENAI_API_KEY` and `CHEAP_MODEL` for AI analysis.
- Adzuna (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) or Apify (`APIFY_MCF_RUN_URL`, `APIFY_API_TOKEN`)
  for live job listings. Alternatively, set `ALLOW_DEMO_DATA=true` to use the bundled sample jobs.

Start both services:

```bash
npm run dev:api   # http://localhost:8000
npm run dev:web   # http://localhost:3000
```

Or use Docker:

```bash
docker compose up --build
```

To try it out, upload `examples/resume_ai_engineer.txt`.

## Tests

```bash
npm run test            # backend and security tests
npm run eval:deepeval   # AI quality evals
npm run eval:promptfoo  # prompt-injection red-team checks
npm run e2e             # Playwright end-to-end tests
```

None of the eval gates need API keys.

## License

Shared for learning and reference. Feel free to explore the code.
