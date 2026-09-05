from __future__ import annotations

import asyncio

import pytest
from app.services import job_sources


def test_singapore_job_failure_is_exposed_without_demo_substitution(monkeypatch) -> None:
    calls = 0

    async def unavailable(_target_role: str, _limit: int):
        nonlocal calls
        calls += 1
        raise TimeoutError("provider unavailable")

    monkeypatch.setattr(job_sources, "_fetch_mycareersfuture_jobs", unavailable)
    job_sources._JOB_CACHE.clear()

    with pytest.raises(job_sources.JobSourceUnavailable, match="no roles were substituted"):
        asyncio.run(job_sources.fetch_jobs("AI Engineer", "Singapore", 5))

    assert calls == 1


def test_demo_jobs_require_explicit_configuration(monkeypatch) -> None:
    async def empty(_target_role: str, _limit: int):
        return []

    monkeypatch.setattr(job_sources, "_fetch_mycareersfuture_jobs", empty)
    monkeypatch.setattr(job_sources.settings, "allow_demo_data", True)
    job_sources._JOB_CACHE.clear()

    jobs, mode, _cache_hit = asyncio.run(job_sources.fetch_jobs("Data Analyst", "Singapore", 5))

    assert jobs
    assert mode == "demo"
