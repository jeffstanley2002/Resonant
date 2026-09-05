# Demo Guide

Use this guide for portfolio recording, recruiter screenshares, or a quick live walkthrough after deployment.

## Fast Demo Path
1. Open the deployed Vercel URL.
2. Sign in with Supabase Auth, or use local demo mode before production.
3. Upload `examples/resume_ai_engineer.txt`.
4. Search for `AI Engineer` in `Singapore` with a limit of `30`.
5. Point out the top fit score, matched skills, missing skills, fit explanation, model/cost telemetry, and cache status.
6. Save the best match.
7. Submit a `5` rating to show the governance feedback loop.
8. Use `Delete my data` to show user-controlled application data deletion.
9. Trigger or describe a provider failure and show that the UI exposes the failed stage without synthetic recommendations.

Before a live walkthrough, run:
```bash
npm run smoke:demo -- --api http://127.0.0.1:8000
```

After deployment, run the same workflow against Render with a Supabase access token:
```bash
JOBMATCH_BEARER_TOKEN=<supabase-access-token> \
  npm run smoke:demo -- --api https://your-render-service.onrender.com
```

## Security Demo Path
1. Show [SECURITY_CHECKLIST.md](/Users/jeffrey/Desktop/projects/job/SECURITY_CHECKLIST.md).
2. Show Supabase RLS policies in `supabase/migrations/001_initial_schema.sql`.
3. Show backend auth guard and CSRF-bound cookie fallback in `apps/api/app/core/auth.py`.
4. Show upload validation in `apps/api/app/services/resume_parser.py`.
5. Show redacted logging and response trimming tests.
6. Show user-scoped application data deletion in `apps/api/app/api/routes/account.py`.
7. Run `npm run security:scan` and `npm run audit`.

## Eval + Governance Demo Path
1. Show [EVALUATION_AND_GOVERNANCE.md](/Users/jeffrey/Desktop/projects/job/EVALUATION_AND_GOVERNANCE.md).
2. Run `npm run eval:deepeval`.
3. Run `npm run eval:promptfoo`.
4. Explain that model output is treated as untrusted and all final responses are schema-validated.
5. Show `examples/resume_prompt_injection.txt` as a safe red-team fixture.

## Cost-Control Demo Path
1. Show [COST_CONTROL.md](/Users/jeffrey/Desktop/projects/job/COST_CONTROL.md).
2. Show model routing in `apps/api/app/services/model_router.py`.
3. Show TTL caches in `apps/api/app/core/cache.py`.
4. Run a match twice and point out `job cache hit` on the second run.
5. Explain provider failover, validated structured outputs, local semantic ranking, and the internal skill-overlap score cross-check.

## Talk Track
Resonant is a production-style AI agent for job search. It uses LangGraph to orchestrate resume parsing, skill extraction, job retrieval, ranking, and persistence. I built it with security, governance, and cost controls from the start: Supabase RLS, server-side auth, upload restrictions, evals, prompt-injection checks, model routing, caching, and free-tier deployment on Vercel, Render, and Supabase.
