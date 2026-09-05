# Architecture Essentials

## What This System Does
Resonant turns a resume into ranked job opportunities with fit scores, skill gaps, and coaching. It is designed as a secure, free-tier, resume-worthy AI engineering portfolio project.

## Tech Stack
- Next.js + TypeScript frontend on Vercel Hobby.
- FastAPI backend on Render Free.
- LangGraph for the agent workflow.
- Supabase Auth/Postgres on Supabase Free; raw resume object storage is intentionally omitted.
- DeepEval and Promptfoo for evaluation and red-team checks.
- Helicone for deployed LLM monitoring; Langfuse OSS optional later.
- Amplitude Free for privacy-safe product analytics.

## Repository Structure
- `apps/web`: frontend.
- `apps/api`: backend.
- `packages/shared`: shared TypeScript schemas/types.
- `supabase`: migrations and RLS policies.
- `evals/deepeval`: Python LLM quality tests.
- `evals/promptfoo`: prompt and red-team configs.
- `examples`: safe demo resumes and red-team fixtures.
- `tests`: deterministic API/security tests.
- `scripts`: setup, scan, and verification helpers.

## Major Components
- UI dashboard: resume upload, search controls, ranked matches, saved jobs, feedback, data deletion.
- API routes: health, account data deletion, resume analysis, agent matching, saved jobs, feedback.
- Agent workflow: resolve the user-owned resume analysis, extract skills, fetch jobs, normalize jobs, rank candidates with local semantic similarity and skill overlap, generate coaching, and persist results.
- LLM coaching enrichment must be structured JSON, validated, sanitized, and limited to top matches.
- Security layer: server-side auth, RLS, app-layer encryption, validation, upload restrictions,
  response trimming.
- Cost layer: model routing, caps, in-process caching, token/cost metadata, and provider failover.

## Core Data Models
- `profiles`
- `resume_analyses`
- `job_searches`
- `job_matches`
- `saved_jobs`
- `feedback`
- `agent_runs`

## Important Data Flows
- Browser authenticates with Supabase Auth.
- Browser calls FastAPI with bearer token.
- Browser sends `X-Turnstile-Token` for upload/matching when Turnstile is configured.
- FastAPI validates token server-side.
- FastAPI performs upload parsing and job matching.
- Supabase RLS enforces user-owned data.
- Backend returns only trimmed public response fields.
- User-triggered data deletion removes application-owned rows through authenticated backend routes.

## External Integrations
- Supabase for auth and data.
- Adzuna-compatible job API.
- LiteLLM-compatible LLM providers.
- Helicone for LLM monitoring.
- Amplitude for non-sensitive product analytics.

## Critical Architectural Rules
- Never hardcode secrets.
- Never expose Supabase service-role keys to the frontend.
- Never expose `APP_ENCRYPTION_KEY` to the frontend.
- Enable RLS on every exposed Supabase table.
- Treat LLM output as untrusted input.
- Never log resume text, tokens, or secrets.
- Production readiness requires a valid Fernet `APP_ENCRYPTION_KEY`.
- Never auto-apply to jobs.
- Never present deterministic replacement content as AI output; expose failed or partial AI stages.
- Demo job data must be explicitly enabled and clearly labeled.
- User data deletion must stay scoped by server-derived `user_id`.

## Important Constraints
- Must run on free tiers.
- Render may sleep when idle.
- Supabase Free has size/inactivity limits.
- AI provider free quotas can be low.

## Key Decisions
- Separate frontend/backend for security and portfolio credibility.
- Supabase Auth instead of custom password handling.
- API aggregator instead of scraping.
- Helicone first, Langfuse OSS later.
- Promptfoo stands in for unclear “Potshot” tooling.
- Local TF-IDF semantic ranking improves job retrieval quality without provider costs, new secrets, or a vector database.
