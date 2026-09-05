# Cost Control

## Goal
The app must be impressive while staying usable on student/free tiers. Cost control is a product requirement, not an afterthought.

## Model Routing
Use a small router around LiteLLM-compatible providers:
- `extract`: cheapest/free model for structured resume understanding.
- `normalize`: cheapest/free model for structured job analysis.
- `match`: cheapest/free model first for grounded comparisons on capped candidates.
- `rank`: cheapest/free model first for final ranking synthesis.

Provider model IDs are configured with `CHEAP_MODEL`; `STRONG_MODEL` is optional fallback only.
Do not hardcode a free model name in code because provider catalogs and free quotas change.

## Default Caps
- Analyze 30 jobs by default.
- Hard cap at 40 jobs per run.
- Limit upload size to 5 MB.
- Limit per-user match runs per day.
- Limit LLM retries to one retry per provider.
- Cap each model attempt at 24 seconds and each routed task at a 60-second wall-clock budget.

## Caching
- Cache parsed resume uploads by file hash for 30 minutes.
- Cache deterministic skill evidence used by tests and cross-checks for 30 minutes.
- Cache fetched job lists by provider, country, target role, location, and limit for 10 minutes.
- Return copied cached objects so callers cannot mutate shared cache state.
- Reuse persisted validated resume analysis by `resume_id` instead of analyzing the resume again.

## Monitoring
Track:
- Model used.
- Estimated input/output tokens.
- Estimated cost.
- Latency.
- Cache hit/miss.
- Fallback reason.
- Error class, redacted.

When `HELICONE_API_KEY` is configured, LiteLLM sends model-call telemetry through its Helicone
callback with app and task metadata. The credential is never forwarded as a model-provider header.
Enabling Helicone is an explicit choice to observe model traffic; dashboard retention must be
configured consistently with the resume-data policy.

## Free-Tier Defaults
- Vercel Hobby for frontend.
- Render Free for backend.
- Supabase Free for auth/database.
- Amplitude Free for product analytics.
- Helicone Hobby for LLM monitoring.
- DeepEval/Promptfoo local evals.

## Degradation Behavior
If free quotas are exhausted:
- The router tries a configured secondary provider within the task budget.
- Live job providers fail over to another live source; demo jobs appear only when explicitly enabled.
- A failed required AI stage returns no recommendations.
- The workflow does not call a coaching model.
- UI shows the exact failed stage and never substitutes deterministic AI text for failed required work.
