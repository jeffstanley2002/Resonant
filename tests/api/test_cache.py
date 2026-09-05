from __future__ import annotations

import asyncio
import io

from app.services.job_sources import _JOB_CACHE, _demo_jobs, fetch_jobs
from app.services.resume_parser import _PARSED_RESUME_CACHE, parse_upload
from app.services.skill_extractor import _SKILL_CACHE, extract_skills
from fastapi import UploadFile
from starlette.datastructures import Headers


def test_resume_parser_caches_by_file_hash(monkeypatch) -> None:
    calls = 0
    _PARSED_RESUME_CACHE.clear()

    def extract_text(_content: bytes, _extension: str) -> str:
        nonlocal calls
        calls += 1
        return "Python FastAPI Supabase LangGraph portfolio engineer"

    monkeypatch.setattr("app.services.resume_parser._extract_text", extract_text)

    first = asyncio.run(parse_upload(txt_upload()))
    second = asyncio.run(parse_upload(txt_upload()))

    assert calls == 1
    assert first == second


def test_skill_extractor_returns_copied_cached_skills() -> None:
    _SKILL_CACHE.clear()

    first = extract_skills("Python React Supabase")
    first.clear()
    second = extract_skills("Python React Supabase")

    assert [skill.name for skill in second] == ["Python", "React", "Supabase"]


def test_job_source_reports_cache_hits_and_returns_copies(monkeypatch) -> None:
    _JOB_CACHE.clear()
    monkeypatch.setattr("app.services.job_sources.settings.adzuna_app_id", "")
    monkeypatch.setattr("app.services.job_sources.settings.adzuna_app_key", "")
    monkeypatch.setattr("app.services.job_sources.settings.apify_mcf_run_url", "")
    monkeypatch.setattr("app.services.job_sources.settings.apify_api_token", "")
    monkeypatch.setattr("app.services.job_sources.settings.allow_demo_data", True)

    first_jobs, first_mode, first_hit = asyncio.run(fetch_jobs("AI Engineer", "Remote", 2))
    first_jobs[0].title = "Mutated"
    second_jobs, second_mode, second_hit = asyncio.run(fetch_jobs("AI Engineer", "Remote", 2))

    assert first_mode == "demo"
    assert second_mode == "demo"
    assert first_hit is False
    assert second_hit is True
    assert second_jobs[0].title != "Mutated"


def test_demo_job_source_offers_a_useful_singapore_result_set() -> None:
    jobs = _demo_jobs(30)

    assert len(jobs) >= 10
    assert all("Singapore" in job.location for job in jobs)


def txt_upload() -> UploadFile:
    return UploadFile(
        filename="resume.txt",
        file=io.BytesIO(b"Python FastAPI Supabase LangGraph portfolio engineer"),
        headers=Headers({"content-type": "text/plain"}),
    )
