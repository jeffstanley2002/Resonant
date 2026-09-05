from __future__ import annotations

from app.services.agent import _trim_telemetry
from app.services.job_sources import (
    _normalize_adzuna_job,
    _normalize_apify_mycareersfuture_job,
    _normalize_mycareersfuture_job,
)


def test_telemetry_trimming_removes_sensitive_fields() -> None:
    telemetry = _trim_telemetry(
        {
            "run_id": "run_123",
            "model": "deterministic",
            "api_key": "secret",
            "resume_text": "private",
        }
    )

    assert telemetry == {"run_id": "run_123", "model": "deterministic"}


def test_telemetry_trimming_keeps_cost_controls() -> None:
    telemetry = _trim_telemetry(
        {
            "estimated_cost_usd": 0.001,
            "model_fallback": True,
            "provider": "local",
            "job_cache_hit": True,
            "secret": "never",
        }
    )

    assert telemetry == {
        "estimated_cost_usd": 0.001,
        "model_fallback": True,
        "provider": "local",
        "job_cache_hit": True,
    }


def test_job_source_trims_long_descriptions() -> None:
    job = _normalize_adzuna_job(
        {
            "id": "job_1",
            "title": "Engineer",
            "company": {"display_name": "Example"},
            "location": {"display_name": "Remote"},
            "description": "Python " * 1000,
            "redirect_url": "https://example.com/job",
        }
    )

    assert len(job.description) <= 2000


def test_apify_job_source_normalizes_and_sanitizes_html() -> None:
    job = _normalize_apify_mycareersfuture_job(
        {
            "jobPostId": "MCF-2026-0000001",
            "title": "AI Engineer",
            "companyName": "Example Pte Ltd",
            "location": ["Raffles Place", "Singapore"],
            "descriptionHtml": "<p>Python and LangGraph</p><script>alert('x')</script>",
            "url": "https://www.mycareersfuture.gov.sg/job/MCF-2026-0000001",
            "salaryMin": "4500",
            "salaryMax": 7000,
        }
    )

    assert job.external_id == "MCF-2026-0000001"
    assert job.source == "apify_mycareersfuture"
    assert "<script" not in job.description
    assert job.salary_min == 4500
    assert job.salary_max == 7000


def test_mycareersfuture_job_source_normalizes_nested_shape() -> None:
    job = _normalize_mycareersfuture_job(
        {
            "uuid": "abc123",
            "title": "Senior Software Engineer",
            "description": "<p>Build Python APIs</p>",
            "company": {"name": "Example Singapore"},
            "salary": {"minimum": 6000, "maximum": 8000},
            "address": {"block": "1", "street": "Fusionopolis View", "postalCode": "138577"},
            "metadata": {
                "jobPostId": "MCF-2026-0000002",
                "jobDetailsUrl": "https://www.mycareersfuture.gov.sg/job/example",
            },
        }
    )

    assert job.external_id == "MCF-2026-0000002"
    assert job.company == "Example Singapore"
    assert job.location == "1, Fusionopolis View, 138577"
    assert job.salary_min == 6000
    assert job.source == "mycareersfuture"
