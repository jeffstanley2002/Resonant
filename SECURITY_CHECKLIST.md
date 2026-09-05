# Security Checklist

This file maps the requested security requirements to repository controls.

| # | Requirement | Implementation Control |
|---|---|---|
| 1 | Hide API keys | `.env.example`, `.gitignore`, backend-only config, secret scan script |
| 2 | Purge Git secrets | Documented in `scripts/purge_git_secrets.md`; optional pre-commit hook blocks common leaks before first push |
| 3 | Use public DB key | Frontend uses only `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| 4 | Enable row-level security | Supabase migration enables RLS on every user table |
| 5 | Encrypt sensitive data | No raw resume storage by default; persisted resume analysis payloads are app-layer encrypted with backend-only `APP_ENCRYPTION_KEY` in production |
| 6 | Enforce server-side auth | FastAPI dependencies validate bearer tokens before protected routes |
| 7 | Lock record access | RLS policies, backend ownership checks, and user-scoped deletion |
| 8 | Block field tampering | Pydantic/Zod schemas and server-derived `user_id` |
| 9 | Secure session cookies | Supabase Auth plus backend `HttpOnly`, `Secure` production session cookie with CSRF-bound cookie fallback |
| 10 | Hash passwords | Delegated to Supabase Auth |
| 11 | Rate limit login | Supabase Auth protections plus backend rate limiter for protected expensive endpoints |
| 12 | Add bot protection | Rate limits, upload caps, optional Cloudflare Turnstile widget, CORS-approved `X-Turnstile-Token`, and backend verification via `TURNSTILE_SECRET_KEY` |
| 13 | Parameterize queries | Supabase client/query builders and SQL migrations only |
| 14 | Validate all input | Pydantic backend schemas and Zod/shared frontend schemas |
| 15 | Escape user content | React escapes rendered strings by default; no raw HTML rendering |
| 16 | Restrict file uploads | File size, extension, and MIME validation |
| 17 | Trim API responses | Response schemas expose only client-safe fields |
| 18 | Add security headers | FastAPI middleware and Next.js headers config, including CSP support for optional Turnstile |
| 19 | Force HTTPS | Vercel/Render managed TLS plus HTTPS deployment docs |
| 20 | Scan dependencies | npm audit and pip-audit are wired into local commands and CI |

## Implemented Evidence
- Backend auth guard: `apps/api/app/core/auth.py`.
- CSRF-bound cookie fallback: `apps/api/app/core/auth.py` and `apps/api/app/api/routes/session.py`.
- Rate limiting: `apps/api/app/core/rate_limit.py`.
- Optional bot protection: `apps/api/app/core/bot_protection.py`.
- Upload restrictions: `apps/api/app/services/resume_parser.py`.
- App-layer encryption: `apps/api/app/core/encryption.py` and `apps/api/app/services/storage.py`.
- Prompt/HTML sanitization: `apps/api/app/services/sanitization.py`.
- Response trimming: `apps/api/app/services/agent.py`.
- User data deletion: `apps/api/app/api/routes/account.py` and `apps/api/app/services/storage.py`.
- Frontend security headers: `apps/web/next.config.mjs`.
- Backend security headers: `apps/api/app/main.py`.
- RLS policies: `supabase/migrations/001_initial_schema.sql`.
- Secret scanner: `scripts/scan_secrets.py`.
- Optional local pre-commit hook installer: `scripts/install_git_hooks.py`.
- Dependency audit command: `npm run audit`.

## Non-Negotiables
- Never commit `.env` or provider keys.
- Never put Supabase service-role keys in `apps/web`.
- Never put `APP_ENCRYPTION_KEY` in `apps/web` or Vercel.
- Never log resume contents.
- Never trust model output without schema validation.
- Never disable RLS to “fix” an app bug.
