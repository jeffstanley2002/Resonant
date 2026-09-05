# PRD: Resonant

## Product Overview
Resonant is a portfolio-grade job discovery assistant that helps candidates turn a resume into a focused job-search plan. A user uploads a resume, enters target roles and locations, and receives ranked job matches with fit scores and skill gaps.

## Problem Statement
Job seekers waste time scanning large job boards, guessing which roles fit them, and rewriting applications without a clear view of their strongest opportunities. Existing tools often feel generic, do not explain why a job is a fit, and rarely help users prioritize action.

## Target Users
- Students and early-career candidates preparing applications.
- Career switchers who need to map existing skills to realistic roles.
- Portfolio reviewers or recruiters evaluating this project as an AI engineering demonstration.

## Main User Workflows
- Create an account with Supabase Auth.
- Upload a resume in PDF, DOCX, or TXT format.
- Review extracted skills, roles, experience signals, and missing information.
- Search for jobs by title, location, and work mode.
- Receive ranked jobs with match explanations, risks, gaps, and next actions.
- Save jobs and provide feedback on recommendation quality.
- Delete application data when the user wants to clear saved jobs, analyses, feedback, and agent runs.

## Core Features
- Authenticated resume upload with strict file validation.
- Resume parsing and skill extraction.
- API-backed job search through an aggregator such as Adzuna.
- LangGraph-powered job matching workflow.
- Fit score, evidence, and skill gaps for each match.
- Saved jobs and recommendation feedback.
- User-controlled application data deletion.
- Cost-aware model routing with provider failover and explicit AI failure states.
- Evaluation, governance, monitoring, and security checklists.

## Nice-To-Have Features
- Cover letter and resume bullet rewriting.
- Company research summaries.
- Interview prep cards.
- Calendar/task integrations.
- Browser extension for saving jobs from external boards.
- Langfuse self-hosted observability.

## Out-Of-Scope Features
- Automatically applying to jobs.
- Scraping job boards without explicit permission.
- Paid-only infrastructure as a hard requirement.
- Custom password authentication.
- Recruiter-facing candidate marketplace.
- Enterprise team administration.

## Functional Requirements
- Users can authenticate and access only their own data.
- Users can upload one resume per analysis run.
- The system parses resume text deterministically and requires validated AI analysis for candidate facts.
- The system fetches live job listings when aggregator credentials are configured.
- Demo jobs are used only when explicitly enabled and are always labeled as curated data.
- The system uses deterministic signals only to select/cross-check candidates; visible reasoning and final ranking require validated AI output.
- The UI displays clear loading, error, empty, and quota-exhausted states.
- The system records non-sensitive analytics events.
- The system lets users delete application-owned data without deleting their Supabase Auth account.

## Non-Functional Requirements
- Free-tier deployable on Vercel, Render, and Supabase.
- Secure by default with no committed secrets.
- Sensitive resume-derived data encrypted before production persistence.
- Explicit failed or partial states when AI or job providers fail, without synthetic replacement output.
- Deterministic tests for core scoring and validation.
- LLM behavior covered by DeepEval and Promptfoo suites.
- Minimal latency through caching and capped job analysis.

## Success Criteria
- A first-time reviewer can understand and run the project from `README.md`.
- A user can upload a resume and see useful job matches in demo mode.
- Live job search works after API keys are configured.
- All documented security controls are represented in code, migrations, or checks.
- Evals and tests can be run locally.
- The project clearly demonstrates AI engineering, security, cost control, and product taste.
- A recruiter walkthrough can use safe sample resumes without exposing real personal data.

## Assumptions
- Supabase Auth handles password hashing and session lifecycle.
- The browser receives only the Supabase publishable/anon key.
- Service-role and job API keys are backend-only.
- Adzuna is the default job aggregator for v1.
- Free LLM providers may have low rate limits, so provider failover and clear retryable failure states are required.
- Resume files may contain sensitive personal data and should be minimized.

## Constraints
- The user is a student and wants free-tier infrastructure.
- Render Free services can sleep when idle.
- Supabase Free has storage/database limits and inactivity behavior.
- AI provider tiers may change quotas.
- The MVP should impress without becoming too broad to finish.

## Important Edge Cases
- Empty or image-only resume files.
- Oversized uploads.
- Malicious file names or spoofed content types.
- Prompt injection inside resumes or job descriptions.
- Job API outage, quota exhaustion, or malformed responses.
- Duplicate analysis submissions.
- Multiple concurrent runs for the same user.
- LLM outputs that omit required fields or invent facts.

## Open Questions
- Which job API keys will be available at deployment time?
- Which free LLM provider will be easiest for the user to obtain?
- Whether resume source files should be retained at all after parsing.
- Whether user feedback should be used only for local improvement or future personalization.
