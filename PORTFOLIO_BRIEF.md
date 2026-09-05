# Portfolio Brief

## Project Pitch
Resonant is a secure AI job-search agent that turns a resume into ranked job matches,
and skill-gap insights. It is built as a production-style portfolio app with
LangGraph orchestration, Supabase RLS, FastAPI, Next.js, evals, red-team checks, and
free-tier deployment paths.

## Resume Bullets
- Built a full-stack AI job-matching agent with Next.js, FastAPI, LangGraph, Supabase,
  and cost-aware provider routing for structured resume analysis, job reasoning, and ranking.
- Designed production-grade security controls including Supabase row-level security,
  server-side auth guards, strict upload validation, response trimming, rate limits,
  secret scanning, and dependency audits.
- Added AI governance with DeepEval quality tests, Promptfoo prompt-injection checks,
  schema/evidence-validated LLM outputs, explicit failed/partial stages, and token/cost telemetry.
- Added embedding-style semantic vector ranking with local TF-IDF/cosine similarity to improve
  job retrieval quality without provider cost or a vector database.
- Containerized the FastAPI AI service and added a local Docker Compose stack for portable demos.
- Implemented a polished portfolio demo with resume upload, ranked matches, saved jobs,
  feedback analytics, user-controlled data deletion, Playwright coverage, and deploy-ready
  Vercel/Render/Supabase docs.

## Interview Story
The project demonstrates that I can build more than a chatbot. I designed an agentic
workflow, controlled costs with routing and bounded AI stages, handled sensitive resume data
carefully, and added evaluation gates so model output is treated as an untrusted system
dependency.

## Technical Proof Points
- Agent workflow: `parse_resume -> analyze_resume -> fetch_jobs -> analyze_jobs -> select_candidates -> reason_matches -> synthesize_ranking -> validate_output -> persist_results`.
- Security: all protected routes require server-side auth, backend-only Supabase service
  role usage, RLS policies for user-owned records, user-scoped data deletion, and no raw
  resume text in analytics.
- Cost control: task-aware model routing, provider failover, job/model caps, cacheable
  resume parsing, daily match limits, local semantic ranking, and an internal skill-overlap cross-check.
- Governance: DeepEval groundedness and ranking metrics plus executable Promptfoo
  boundary tests for injection, HTML, cap bypass, and malformed model output.
- Observability: structured redacted provider-failover logs, LLM model/latency/token/cost telemetry,
  implemented LiteLLM-to-Helicone callback support, and privacy-safe Amplitude integration support.
- Verification: 109 backend/security/DeepEval tests, six Playwright workflows, five Promptfoo
  boundary cases, frontend/backend lint, TypeScript, production build, secret scan, strict UI audit,
  and pip-audit reproduced locally on 2026-09-04. npm audit remains registry-blocked and is not claimed.

## Demo Script
1. Open the deployed app and sign in with Supabase Auth.
2. Upload `examples/resume_ai_engineer.txt` or use the built-in sample resume.
3. Search for `AI Engineer` in `Singapore`.
4. Show ranked jobs, matched skills, missing skills, and fit explanation.
5. Save a job and submit a recommendation-quality rating.
6. Use `Delete my data` to show privacy/data-lifecycle control.
7. Show the docs, tests, security checklist, and eval suite as evidence of engineering discipline.
8. Use `examples/resume_prompt_injection.txt` to explain red-team thinking without exposing real personal data.

## Honest Limitations
- Free-tier AI and job APIs can rate-limit; the app exposes failed/partial stages and never substitutes synthetic AI output.
- Render Free may sleep after inactivity, causing cold starts.
- Supabase, Helicone, Amplitude, Adzuna/Apify, and live LLM integrations are implemented but should be described as such until deployment screenshots or logs prove active use.
- Provider embeddings, RAG, and a vector database are intentionally omitted because local TF-IDF
  handles bounded resume/job ranking for v1; future company research is the appropriate RAG extension.
