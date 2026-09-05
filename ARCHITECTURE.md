# Architecture: Resonant

## System Architecture
Resonant is a monorepo with a Next.js frontend, a FastAPI backend, Supabase for auth/database, and a LangGraph agent workflow for resume-to-job matching. Raw resume files are parsed in memory and deliberately not retained in object storage.

### Major Components
- Web app: account flow, upload surface, job search controls, match dashboard, saved jobs, and feedback.
- API service: authentication enforcement, optional Turnstile verification, upload validation,
  job aggregation, agent orchestration, response trimming, and analytics-safe event emission.
- Supabase: user identity, Postgres data, storage metadata, RLS policies, and least-privilege grants.
- Agent workflow: resume parsing, skill extraction, job fetching, normalization, scoring, coaching, and persistence.
- Evaluation stack: unit/integration tests, DeepEval quality checks, Promptfoo red-team suites, and security scripts.
- Observability: structured logs, Helicone for deployed LLM monitoring, and optional Langfuse OSS for deeper local tracing.

### Component Communication
- Browser talks to Supabase Auth for user sessions and to FastAPI for protected application operations.
- Backend session cookies are `HttpOnly`; cookie-auth fallback requires a matching CSRF token.
- Browser sends `X-Turnstile-Token` on expensive protected operations when Turnstile is configured.
- Frontend CSP allows Cloudflare Turnstile script/frame origins without allowing arbitrary scripts.
- FastAPI validates Supabase JWTs server-side before accessing user-owned resources.
- FastAPI talks to Supabase using backend-only credentials for server-owned writes.
- FastAPI encrypts persisted resume-analysis payloads with `APP_ENCRYPTION_KEY` when configured.
- FastAPI calls job APIs and LLM providers through typed service boundaries.
- The model router and agent telemetry record latency, token estimates, selected model, job-cache
  hits, and fallback status.

### Request/Data Flow
1. User signs in with Supabase Auth.
2. User uploads a resume to the FastAPI backend.
3. Backend validates file type, size, auth, and optional bot-protection token.
4. Backend extracts text, derives skills, and stores only necessary metadata/results; in production,
   resume-derived analysis details are stored in an app-layer encrypted payload.
5. User requests job matches with the user-owned `resume_id` and title/location preferences.
6. LangGraph resolves that encrypted analysis, fetches jobs, runs AI job analysis, selects candidates with a deterministic local semantic ranker plus an internal skill-overlap cross-check, runs AI match reasoning, synthesizes the final AI ranking, generates AI coaching, validates output, and persists the run.
7. Backend trims internal fields and returns ranked matches.
8. UI displays results and records non-sensitive analytics events.

### External Services
- Supabase Auth/Postgres. Object storage is excluded because the MVP does not retain raw resumes.
- Adzuna or compatible job search API.
- Free or low-cost LLM providers routed through LiteLLM-compatible code.
- Helicone for LLM request monitoring.
- Amplitude for product analytics.

## Tech Stack

### Next.js + TypeScript
- Used for the Vercel-hosted frontend.
- Selected for deploy speed, resume value, strong ecosystem, and typed UI.
- Alternatives: Remix, SvelteKit, Vite SPA.
- Trade-off: Next.js is heavier than a SPA, but portfolio credibility and deployment ergonomics are strong.

### FastAPI + Python
- Used for backend APIs and AI workflow orchestration.
- Selected because LangGraph, DeepEval, and data-processing tools are Python-native.
- Alternatives: Express/NestJS, Django, serverless functions.
- Trade-off: Render Free cold starts can be noticeable, but backend separation is clearer and more impressive.

### LangGraph
- Used for explicit, inspectable agent workflow orchestration.
- Selected for stateful graphs, checkpoint-ready state, and production AI-engineering credibility.
- Alternatives: simple function pipeline, LangChain agents, CrewAI.
- Trade-off: More structure than a basic chain, but useful for evaluation, observability, and future human review.

### Supabase
- Used for auth, Postgres, RLS, and optional object storage.
- Selected for free tier, fast setup, and strong security primitives.
- Alternatives: Firebase, Neon + Auth.js, Render Postgres.
- Trade-off: RLS must be designed carefully and tested.

### DeepEval + Promptfoo
- DeepEval is used for Python LLM regression tests.
- Promptfoo is used for declarative prompt evals and red-team checks.
- Alternatives: OpenAI Evals, LangSmith evals, Braintrust.
- Trade-off: Some LLM-as-judge tests require provider keys, so deterministic eval subsets must exist.

### Helicone + Amplitude
- Helicone tracks LLM usage, latency, cost, provider failover, and failed calls.
- Amplitude tracks product events without sensitive resume data.
- Alternatives: Langfuse, PostHog, LangSmith.
- Trade-off: Helicone Cloud is simpler than self-hosting Langfuse; Langfuse remains optional.

## Backend Design

### API Structure
- `GET /health`: service health and deployment smoke test.
- `POST /resumes/analyze`: authenticated upload, validation, parsing, and skill extraction.
- `POST /agent/matches`: authenticated job search and LangGraph matching workflow.
- `POST /feedback`: authenticated recommendation feedback without sensitive payloads.

### Services
- `auth`: server-side Supabase token validation.
- `resume_parser`: PDF/DOCX/TXT extraction and upload safety checks.
- `skill_extractor`: internal deterministic evidence cross-check; never a user-facing AI replacement.
- `job_sources`: live provider chain with redacted failover telemetry and explicitly enabled demo data.
- `cache`: short-lived in-process caches for parsed resumes, extracted skills, and fetched jobs.
- `semantic_search`: local TF-IDF/cosine similarity for no-cost resume-to-job semantic ranking.
- `scoring`: internal deterministic candidate baseline that blends skill overlap with local semantic similarity; never a visible explanation or coaching source.
- `model_router`: task-aware provider selection, one transient retry, secondary providers, explicit failure results, and cost/token metadata.
- `agent`: required LangGraph graph with typed failed and partial stage states.
- `storage`: Supabase persistence boundary.
- `encryption`: Fernet app-layer encryption for sensitive resume-analysis persistence.

### Business Logic
- Never trust frontend user IDs; derive user identity from the validated token.
- Cap jobs analyzed per run.
- Cache repeat resume parsing and normalized job data where possible.
- Treat all LLM outputs as untrusted and validate with Pydantic models.
- Return no AI content when required model stages fail; expose the exact failed or partial stage.

### Background Jobs
No separate worker is required for MVP. Long-running matching remains request-scoped with strict caps. A future worker can be added if match runs exceed Render Free limits.

### Authentication/Authorization
Supabase Auth is the identity provider. The backend verifies bearer tokens against Supabase before protected work. The optional backend session cookie is `HttpOnly` and CSRF-bound. Supabase RLS enforces per-user row access as defense in depth.

## Data Design

### Main Entities
- `profiles`: user profile metadata.
- `resume_analyses`: parsed resume metadata, encrypted analysis payload, and redacted public columns.
- `job_searches`: user search parameters and run metadata.
- `job_matches`: ranked match results and coaching.
- `saved_jobs`: user-saved opportunities.
- `feedback`: recommendation usefulness feedback.
- `agent_runs`: observability metadata for model routing and workflow status.

### Relationships
- A profile owns many resume analyses, job searches, saved jobs, feedback rows, and agent runs.
- A job search owns many job matches.
- A job match may be saved by the same owner.

### Database Choice
Supabase Postgres is the source of truth because it supports relational data, RLS, JSONB, and a useful free tier.

### Example Schemas
See `supabase/migrations/001_initial_schema.sql` for concrete tables, grants, indexes, and policies.

### Indexing Considerations
- Index user-owned tables by `user_id`.
- Index job search/match relationships by `search_id`.
- Index saved jobs by `(user_id, external_job_id)`.
- Use JSONB only for flexible provider payloads and agent metadata.

### Data Lifecycle
- Raw resumes should not be stored by default.
- Extracted text should be minimized and can be deleted after analysis.
- Production deployments require `APP_ENCRYPTION_KEY`; resume summaries, extracted skills, and
  parser warnings are encrypted before persistence.
- Job matches, saved jobs, feedback, resume analyses, and agent telemetry remain until the user
  deletes their application data.
- Logs must not contain resume text, tokens, or secrets.

## AI/ML Architecture

### Model/Provider Strategy
Use a model router with ordered candidates:
1. Free/cheap model for extraction and normalization.
2. Stronger free/low-cost model for final explanations.
3. Explicit failed-stage result when all configured providers are unavailable.

### Prompt Architecture
Prompts live in versioned files/configs under `evals` or backend service constants. Prompts must request structured JSON and explicitly reject resume/job prompt-injection instructions.

### RAG Architecture
No external RAG or vector database is required for MVP. Future company research could add a small retrieval layer.

### Embedding Model / Vector Store
Resonant uses a deterministic local TF-IDF vectorizer with cosine similarity during candidate selection. It compares resume skills and evidence against each job title, description, required skills, preferred skills, responsibilities, and domain context. The final candidate baseline blends 80% skill-overlap scoring with 20% local semantic similarity, so it improves ranking without provider costs, new secrets, or a vector store.

### Agent/Tool Architecture
LangGraph nodes are small, typed, and JSON-serializable:
- `parse_resume`
- `analyze_resume`
- `fetch_jobs`
- `analyze_jobs`
- `select_candidates`
- `reason_matches`
- `synthesize_ranking`
- `generate_coaching`
- `validate_output`
- `persist_results`

### Structured Outputs
All AI-produced objects are validated against Pydantic schemas, job identities, and evidence rules
before use. Malformed required-stage output stops recommendation publication. Invalid coaching is
omitted and marks the run partial; no deterministic text is substituted.

### Evaluation Strategy
- Unit tests for deterministic components.
- DeepEval for output quality and hallucination checks.
- Promptfoo for red-team and prompt regression tests.
- Manual review rubric for fit quality.

### Hallucination Safeguards
- Match explanations must cite resume skills and job requirements.
- The model may not invent experience, certifications, employers, salaries, or eligibility.
- If evidence is missing, say what is unknown.
- Ranking synthesis may reorder only validated job IDs and cannot invent or omit identities.
- Coaching may update explanations and next steps, but cannot alter identity or ownership fields.

### Retry/Fallback Behavior
- Retry transient provider failures once with backoff.
- Fail over to a secondary provider if configured.
- Return an explicit failed stage with no AI content when all model calls fail.

### Observability
Track run ID, route, model, latency, token estimate, fallback reason, cache status, and redacted errors. Do not log resume text.

### Cost and Latency
Use caps, short-lived in-process caching, bounded prompts, local semantic candidate ranking, model routing, and a deterministic skill-overlap cross-check. AI analysis is capped at 12 jobs and coaching at five matches.

## Infrastructure

### Local Development
Run frontend and backend separately. Use `.env.example` as the required variable map.

### Deployment Architecture
- Vercel Hobby hosts `apps/web`.
- Render Free hosts `apps/api`.
- Supabase Free hosts auth and data.

### Environment Variables
Secrets stay outside git. Browser-exposed variables use `NEXT_PUBLIC_` and must not include
service-role secrets. `APP_ENCRYPTION_KEY` is backend-only and required for production readiness.

### Secrets Management
Use Vercel, Render, and Supabase environment managers. Use `.env.example` for documentation only.
Generate `APP_ENCRYPTION_KEY` with `python3 scripts/generate_encryption_key.py` and store it only
in Render or a local ignored `.env` file.

### Logging/Monitoring
Use structured backend logs, Helicone for LLM monitoring, Amplitude for product analytics, and optional Langfuse OSS later.

### CI/CD
GitHub Actions should run lint, type checks, tests, secret scan, dependency audit, and eval smoke tests.

### Scaling Considerations
The MVP is intentionally small. Add a worker queue only when request-scoped matching becomes too slow or unreliable.

## Engineering Decisions
- Keep backend separate from frontend to show real AI service design and avoid exposing secrets.
- Use Supabase Auth rather than custom passwords.
- Store minimum resume data to reduce privacy risk.
- Require AI reasoning for visible recommendations while retaining deterministic safety cross-checks.
- Use Helicone first because it is simpler than self-hosting Langfuse on a student budget.
- Treat Promptfoo as the red-team/eval tool replacing the unclear “Potshot” reference.

## Architecture Critique and Fixes
- Risk: Free LLM quotas can block demos. Fix: provider failover and observable retryable failure states.
- Risk: Resume data is sensitive. Fix: no raw resume storage by default, encrypted persisted
  analysis payloads, redacted logs, and strict upload controls.
- Risk: Job APIs can fail or return malformed data. Fix: provider failover, redacted telemetry, and no silent demo substitution.
- Risk: RLS mistakes can leak data. Fix: migrations include explicit RLS, grants, and policy tests.
- Risk: LangGraph could be overkill. Fix: graph nodes stay simple and mirror real product steps.
- Risk: Eval tools can cost money. Fix: deterministic eval subset runs without judge calls; LLM judge evals are optional.
- Risk: Observability tools can leak private data. Fix: only metadata is logged; content logging is disabled by default.
