# Live AI Evidence

## Evidence Policy
Only redacted runtime metadata belongs in this file. Never record API keys, bearer tokens,
resume text, full prompts, or model responses. A failed run is recorded as a failure and is not
converted into a portfolio claim.

## 2026-09-04 Local AI Provider Smoke

Configuration detected without exposing secrets:
- AI provider configured: yes.
- Model route: OpenAI model IDs configured by `CHEAP_MODEL` and `STRONG_MODEL`.
- Helicone configured: no.
- Safe input: `examples/resume_ai_engineer.txt`.

Attempt 1 used the production defaults (`8s` call timeout, `20s` task budget):
- Resume extraction attempt 1: `TimeoutError`.
- Resume extraction attempt 2: `TimeoutError`.
- API behavior: resume AI status `failed`; zero AI skills; zero recommendations; no synthetic output.

Attempt 2 used smoke-only limits (`30s` call timeout, `60s` task budget):
- Resume extraction attempt 1: `TimeoutError`.
- Resume extraction attempt 2: `TimeoutError`.
- API behavior: failed stage remained explicit; no synthetic output was returned.

Result: live provider routing and honest failure handling are verified. Successful live model output,
token usage, latency, and cost are not yet verified because the configured provider route timed out.

## Required Successful Evidence
Run the following against the deployed API from a reliable provider/network path:

```bash
npm run smoke:demo -- --api <render-url> --skip-write-actions --limit 5
```

A successful redacted JSON record must include:
- `status` equal to `succeeded` or an explained `partial`.
- Non-empty `model` and `provider` values.
- `model_latency_ms`, `input_tokens`, `output_tokens`, `llm_attempts`, and `estimated_cost_usd`.
- `model_fallback` equal to `false`.
- Stage results for resume analysis, job analysis, match reasoning, ranking synthesis, coaching,
  and output validation.
