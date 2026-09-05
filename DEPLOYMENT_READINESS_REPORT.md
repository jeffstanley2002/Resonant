# Deployment Readiness Report

## Status
The project is ready for the user-assisted deployment stage. Local implementation, security
guardrails, evaluation smoke tests, dependency audits, and deployment-prep scripts are in place.

## Verified Locally
- Backend/security/DeepEval tests: 123 passing tests (reproduced 2026-09-05).
- Python lint: Ruff clean.
- Frontend lint: clean.
- TypeScript typecheck: clean.
- Next.js production build: successful.
- Playwright browser tests: 6 passing tests, including explicit AI failure-state coverage
  (reproduced 2026-09-05).
- Secret scan: no obvious secrets found.
- npm audit: 0 vulnerabilities (reproduced 2026-09-05).
- pip-audit: no known vulnerabilities in third-party dependencies (reproduced 2026-09-05;
  local editable package skipped because it is not on PyPI).
- Promptfoo executable red-team suite: 5 passing tests (reproduced 2026-09-05).
- Deployment template check: passes with expected optional-service warnings.
- Production smoke script checks `/health`, `/ready`, frontend availability, and frontend security headers.
- Production deploy check rejects Supabase URL/key drift and half-configured Turnstile.
- Cookie-auth fallback is CSRF-bound with direct security coverage.
- Local TF-IDF semantic ranking is implemented with deterministic API coverage.
- Backend Dockerfile and local Docker Compose stack are present for portable demos.
- Repository hygiene check verifies deploy templates are trackable and local env/build artifacts stay ignored.
- Optional local pre-commit hook installed and verified for secret scan plus repo hygiene.
- Backend npm scripts use a portable Python launcher that selects the local venv when present and CI Python otherwise.
- Live local smoke test passed against real FastAPI and Next.js servers:
  `{"api": "ok", "web": "ok", "security_headers": "ok"}`.
- A previous API smoke covered upload, stored resume ID, MyCareersFuture retrieval, saved-job write,
  and feedback. It did not prove live AI and is not counted as live-model evidence.

## Implemented Product Capabilities
- Resume upload and analysis for PDF, DOCX, and TXT.
- AI-required resume understanding with structured, evidence-validated output.
- Required LangGraph job-matching workflow with explicit failed/partial stage states.
- Local semantic vector ranking blended with deterministic skill-overlap scoring.
- Structured AI job analysis, match reasoning, ranking synthesis, and coaching.
- No synthetic AI output when a model call or validation stage fails.
- Curated demo jobs only when `ALLOW_DEMO_DATA=true`, always labeled as demo data.
- Supabase-ready auth, persistence, and RLS schema.
- Backend-only app-layer encryption for persisted resume analysis payloads.
- Saved jobs and recommendation feedback.
- Implemented support for privacy-safe Amplitude analytics.
- Implemented LiteLLM-to-Helicone monitoring callbacks without forwarding observability credentials to providers.
- Render-ready `/ready` endpoint, Vercel build configuration, and optional local Docker workflow.

## Security Controls
- No committed secrets.
- Backend-only service-role key boundary.
- Backend-only `APP_ENCRYPTION_KEY` required for production readiness.
- Public Supabase anon key only for frontend.
- RLS migration for user-owned tables.
- Server-side auth guards.
- HttpOnly SameSite session cookie support.
- Upload type and size limits.
- Prompt-injection and HTML sanitization.
- Response trimming.
- Security headers.
- Rate limiting.
- Optional Turnstile bot protection.
- npm and Python dependency audits.

## Deployment Inputs Needed From User
- Supabase project URL.
- Supabase anon/publishable key.
- Supabase service-role key for Render only.
- Generated `APP_ENCRYPTION_KEY` for Render only.
- Vercel project/domain.
- Render service URL.
- Optional Adzuna API credentials.
- Optional free LLM provider key and model ID.
- Optional Helicone key.
- Optional Amplitude key.
- Optional Turnstile site/secret keys.

## Recommended Deployment Order
1. Create a clean GitHub commit and push.
2. Run Supabase migration.
3. Create Render backend and set backend env vars.
4. Create Vercel frontend and set frontend env vars.
5. Run `npm run deploy:check:prod` with real production values.
6. Run `npm run smoke:urls -- --api <render-url> --web <vercel-url>`.
7. Demo signup, resume upload, job matching, saved job, and feedback.

## Evidence Still Required Before Resume Claims
- Run `npm run smoke:demo -- --api <render-url>` with a real model provider and retain its redacted JSON output showing status, model, provider, latency, tokens, attempts, fallback status, and estimated cost.
- Capture Helicone/Amplitude/Supabase screenshots only after those deployed integrations are active.

The redacted failed-provider evidence and successful-run acceptance criteria are recorded in
`LIVE_AI_EVIDENCE.md`.
