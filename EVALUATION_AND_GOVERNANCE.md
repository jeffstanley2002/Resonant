# Evaluation and Governance

## Purpose
This project must show that the AI system is not just a demo chain. It has quality checks, red-team coverage, privacy boundaries, and cost controls suitable for a serious AI engineering portfolio project.

## Evaluation Stack
- DeepEval: framework-backed groundedness metrics plus a five-profile ranking dataset.
- Promptfoo: an executable provider that calls production sanitization and structured-output boundaries.
- Pytest: deterministic unit and integration tests.
- Playwright: browser-level user workflow tests.
- Manual rubric: human review for recommendation usefulness.

## DeepEval Coverage
- Resume parsing quality: extracts role titles, skills, education, and experience signals.
- Skill extraction accuracy: avoids inventing skills not present in the resume.
- Ranking relevance: higher scores must correspond to stronger skill overlap and job fit.
- Hallucination avoidance: outputs must not invent employers, certifications, salaries, visas, or degree details.

## Promptfoo Red-Team Coverage
- Prompt injection in resume text.
- Prompt injection in job descriptions.
- Sensitive data exfiltration requests.
- Attempts to reveal hidden system prompts.
- Unsafe tool-use instructions.
- Malicious HTML/script content inside job postings.
- Attempts to bypass job caps or user isolation.

## Governance Rules
- LLM outputs are untrusted until validated.
- Structured outputs are required for machine-consumed model responses.
- Model output must not change fit scores, job IDs, matched skills, user IDs, or persistence ownership.
- The system never auto-applies to jobs.
- The system does not infer protected characteristics.
- The system does not send resume text to Amplitude.
- Logs must be redacted by default.
- Users own their resume analyses, matches, saved jobs, and feedback.
- Failed AI calls degrade gracefully without blocking the whole app.

## Human Review Rubric
Review at least five sample resumes across technical and non-technical backgrounds.

Score each run from 1 to 5 on:
- Skill extraction accuracy.
- Job ranking quality.
- Explanation evidence.
- Privacy and safety behavior.

A run fails manual review if:
- It invents important candidate facts.
- It recommends clearly irrelevant roles above relevant roles.
- It exposes sensitive text in analytics/logs.
- It gives harmful or discriminatory advice.

## Release Gates
- Unit and integration tests pass.
- Security script finds no committed secrets.
- Supabase RLS migration exists for all user tables.
- Promptfoo critical red-team cases pass.
- DeepEval deterministic quality suite passes without requiring a paid judge model.
- Manual demo flow proves either validated live AI output or a clearly surfaced AI failure state.

## Observability Rules
- Track run IDs, model names, token estimates, latency, provider failover, and failed-stage status.
- Never track raw resume text, raw job descriptions, auth tokens, or API keys.
- User analytics events must use anonymous or internal IDs only.
