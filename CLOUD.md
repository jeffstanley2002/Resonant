# Cloud Deployment

## Cloud Provider Choices
- Vercel Hobby for the frontend.
- Render Free for the FastAPI backend.
- Supabase Free for auth, Postgres, and optional storage.
- Amplitude Free for analytics.
- Helicone Hobby for LLM monitoring.

## Why Each Service Exists
- Vercel: fast student-friendly deployment for Next.js.
- Render: simple Python web service deployment.
- Supabase: managed auth, Postgres, RLS, and storage.
- Amplitude: product analytics without building dashboards.
- Helicone: quick visibility into model latency, costs, and failures.

## Development Environment
- Run `apps/web` with Next.js.
- Run `apps/api` with Uvicorn.
- Use local `.env` files ignored by git.
- Use `.env.example` as the source of required variable names.

## Staging Environment
No separate staging environment is required for MVP. Vercel preview deployments can serve as lightweight staging.

## Production Environment
- Vercel production deployment points to the Render backend URL.
- Render production service reads Supabase, app encryption, job API, model provider, and monitoring
  secrets from environment variables.
- Supabase hosts auth and database with RLS.

## Deployment Process
1. Create Supabase project and run migrations.
2. Create Render web service for `apps/api`.
3. Create Vercel project for `apps/web`.
4. Configure environment variables.
5. Run production readiness checks and smoke tests against deployed URLs.

## Networking
- Public browser traffic uses HTTPS.
- Vercel calls Render over HTTPS.
- Render calls Supabase, job API, LLM provider, Helicone, and Amplitude over HTTPS.

## Database Hosting
Supabase Postgres Free is the MVP database. Avoid Render Postgres because free Render Postgres databases expire.

## Object Storage
Supabase Storage may hold uploads only if raw resume retention becomes required. MVP should avoid raw resume retention by default.

## Secrets Management
- Vercel stores `NEXT_PUBLIC_*` values and frontend-only configuration.
- Render stores backend secrets.
- Supabase service-role key is never used in frontend code.
- `APP_ENCRYPTION_KEY` is generated locally, stored only in Render, and required before `/ready`
  passes in production.
- Turnstile is enabled only when both Vercel `NEXT_PUBLIC_TURNSTILE_SITE_KEY` and Render
  `TURNSTILE_SECRET_KEY` are configured.
- Model IDs are configured in Render with `CHEAP_MODEL` and `STRONG_MODEL`; production readiness fails and the UI reports the failed AI stage if no usable model is configured.
- Live jobs use Adzuna when configured, otherwise Apify MyCareersFuture when
  `APIFY_MCF_RUN_URL` and `APIFY_API_TOKEN` are configured.
- Helicone is wired through LiteLLM callbacks when `HELICONE_API_KEY` is set; its credential is not forwarded to model providers.

## Authentication
Supabase Auth manages signup, login, password hashing, recovery, and sessions. Backend validates bearer tokens server-side.

## Logging
Render logs structured JSON metadata only. Do not log resume text, raw job descriptions, API keys, or tokens.

## Monitoring
- Render `/ready` health check for deploy readiness and `/health` for liveness.
- Helicone for LLM calls.
- Amplitude for non-sensitive product analytics.
- Optional Langfuse OSS later if deeper trace UI is needed.

## CI/CD
GitHub Actions should run:
- frontend lint/type checks.
- backend tests.
- security scans.
- eval smoke checks.

## Expected Cost Drivers
- LLM calls.
- Job API usage.
- Storage if raw resumes are retained.
- Analytics volume.
- Backend compute if upgraded.

## Scaling Strategy
Stay simple for MVP. Add a worker queue, persistent cache, and paid compute only if actual usage outgrows free-tier request limits.
