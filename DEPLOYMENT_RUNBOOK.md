# Deployment Runbook

Use this when the project is ready for the actual deploy stage.

## 1. Preflight
```bash
npm install
python3 -m venv apps/api/.venv
apps/api/.venv/bin/python -m pip install --upgrade pip setuptools
apps/api/.venv/bin/pip install -e 'apps/api[dev]'
npm run lint
npm run typecheck
npm run test:api
npm --workspace apps/web run build
npm --workspace apps/web run e2e
npm run security:scan
npm run audit
npm run eval:promptfoo
npm run repo:hygiene
```

## 2. First GitHub Remote And Push
Before connecting Vercel or Render, create clean local commits, connect the GitHub remote, and push manually:
```bash
npm run hooks:install
npm run security:scan
npm run repo:hygiene
git status --short --ignored
git add .
git status --short
git commit -m "docs: rename portfolio project to Resonant"
git branch -M main
git remote add origin https://github.com/jeffstanley2002/Resonant.git
git push -u origin main
```

Prefer a series of focused commits for branding, package metadata, API identity, tests,
Docker, semantic ranking, and deployment documentation instead of one large commit.
Confirm ignored local artifacts such as `.env`, `node_modules`, `.venv`, `.next`, caches, and test
output are not staged. Never commit generated secrets such as `APP_ENCRYPTION_KEY`.

## 3. Optional Local Docker Demo
The standard Render/Vercel deployment remains native to each host, but local Docker is available:
```bash
docker compose up --build
```

This starts the API on `http://localhost:8000` and the web app on `http://localhost:3000`.

## 4. Supabase
1. Create a Supabase Free project.
2. Apply every SQL file in `supabase/migrations/` in numeric order, or use the Supabase CLI.
   For the CLI path, authenticate and link the project first:
   ```bash
   supabase login
   supabase link --project-ref <your-project-ref>
   supabase db push
   ```
   Local Supabase validation requires Docker Desktop to be running.
3. Copy the project URL, anon/publishable key, and service-role key.
4. Keep the service-role key backend-only.
5. Confirm RLS is enabled on:
   - `profiles`
   - `resume_analyses`
   - `job_searches`
   - `job_matches`
   - `saved_jobs`
   - `feedback`
   - `agent_runs`

## 5. Render Backend
Create a Render Free web service from `render.yaml`.
Render uses `/ready` as its health check so production deploys fail fast when
Supabase auth is not configured. `/health` remains a lightweight liveness check.

Required production env:
```text
APP_ENV=production
DEMO_AUTH=false
ALLOW_DEMO_DATA=false
ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
APP_ENCRYPTION_KEY=...
# Configure at least one model route, for example:
OPENAI_API_KEY=...
CHEAP_MODEL=gpt-5.6-luna
STRONG_MODEL=
```

Generate the encryption key locally, then paste it into Render only:
```bash
apps/api/.venv/bin/python scripts/generate_encryption_key.py
```

Optional env:
```text
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
GROQ_API_KEY=...
HELICONE_API_KEY=...
TURNSTILE_SECRET_KEY=...
```

## 6. Vercel Frontend
Set the root directory to `apps/web`.
Vercel will use `apps/web/vercel.json` for the Next.js build settings.

Required production env:
```text
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

Optional env:
```text
NEXT_PUBLIC_AMPLITUDE_API_KEY=...
NEXT_PUBLIC_TURNSTILE_SITE_KEY=...
```

Do not add backend-only secrets to Vercel.
This includes `SUPABASE_SERVICE_ROLE_KEY`, `APP_ENCRYPTION_KEY`, job API keys, LLM provider keys,
Helicone keys, and Turnstile secret keys.

If you enable Turnstile, configure both sides:
- Vercel: `NEXT_PUBLIC_TURNSTILE_SITE_KEY`
- Render: `TURNSTILE_SECRET_KEY`

## 7. Deployment Readiness Check
Copy `.env.production.example` to `.env.production.local`, fill in production values, then run:
```bash
npm run deploy:check:prod
```
This rejects placeholders, frontend/backend Supabase drift, wildcard CORS, HTTP production URLs,
missing encryption, and half-configured Turnstile settings.

## 8. Production Smoke Test
After Vercel and Render deploy:
```bash
python3 scripts/smoke_urls.py \
  --api https://your-render-service.onrender.com \
  --web https://your-vercel-domain.vercel.app
```
This checks API liveness, API readiness, frontend availability, and required
security headers.

Then run the product workflow smoke with a real Supabase access token:
```bash
JOBMATCH_BEARER_TOKEN=<supabase-access-token> \
  npm run smoke:demo -- --api https://your-render-service.onrender.com
```
For a read-only check, add `-- --skip-write-actions` after the API URL.

## 9. Demo Script
1. Open the deployed web app.
2. Sign up or sign in with Supabase Auth.
3. Upload `examples/resume_ai_engineer.txt` first for the cleanest demo.
4. Run a search for `AI Engineer` in `Singapore`.
5. Save the strongest match.
6. Submit a recommendation-quality rating.
7. Show that the app reports the failed AI stage and generates no synthetic output if no LLM key is configured.
8. Use [DEMO_GUIDE.md](/Users/jeffrey/Desktop/projects/job/DEMO_GUIDE.md) for security, eval, cost-control, and red-team talk tracks.

## 10. Rollback
- Vercel: promote the previous deployment.
- Render: redeploy the last successful commit.
- Supabase: avoid destructive migrations; create forward fixes.
