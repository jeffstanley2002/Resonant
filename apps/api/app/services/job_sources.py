from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.core.cache import TTLCache
from app.core.config import settings
from app.core.logging import log_event
from app.schemas import JobPosting
from app.services.sanitization import sanitize_untrusted_text

DEMO_JOBS = [
    {
        "title": "Junior AI Engineer",
        "company": "Northstar Labs",
        "location": "Singapore",
        "description": (
            "Build Python services, LangGraph workflows, prompt evaluations, FastAPI APIs, "
            "and React dashboards for AI products."
        ),
        "url": "https://example.com/jobs/junior-ai-engineer",
    },
    {
        "title": "Full Stack AI Product Engineer",
        "company": "SignalWorks",
        "location": "Singapore",
        "description": (
            "Use TypeScript, Next.js, Python, Postgres, Supabase, and LLM observability "
            "to ship secure AI tools."
        ),
        "url": "https://example.com/jobs/full-stack-ai-product-engineer",
    },
    {
        "title": "Backend Engineer, Applied AI",
        "company": "CraftCloud",
        "location": "Singapore",
        "description": (
            "Design FastAPI services, SQL data models, job queues, model routing, "
            "and production monitoring for LLM systems."
        ),
        "url": "https://example.com/jobs/backend-applied-ai",
    },
    {
        "title": "Frontend Engineer, AI Experiences",
        "company": "CanvasHire",
        "location": "Singapore / Hybrid",
        "description": (
            "Create polished React and Next.js interfaces for AI workflows, analytics, "
            "resume upload, and recommendation feedback."
        ),
        "url": "https://example.com/jobs/frontend-ai-experiences",
    },
    {
        "title": "Machine Learning Platform Engineer",
        "company": "Meridian Systems",
        "location": "One-North, Singapore",
        "description": (
            "Build Python model services, evaluation pipelines, Postgres datasets, "
            "security controls, "
            "and reliable deployment workflows for applied machine learning products."
        ),
        "url": "https://example.com/jobs/ml-platform-engineer",
    },
    {
        "title": "Software Engineer, Generative AI",
        "company": "Harbour Digital",
        "location": "Downtown Core, Singapore",
        "description": (
            "Ship TypeScript and Python features for LLM applications using React, FastAPI, "
            "prompt evaluation, model routing, and production monitoring."
        ),
        "url": "https://example.com/jobs/software-engineer-generative-ai",
    },
    {
        "title": "AI Solutions Engineer",
        "company": "Arcfield Technologies",
        "location": "Singapore / Hybrid",
        "description": (
            "Prototype customer-facing AI workflows with Python, React, LLM APIs, "
            "security reviews, "
            "and clear technical documentation."
        ),
        "url": "https://example.com/jobs/ai-solutions-engineer",
    },
    {
        "title": "Data and AI Engineer",
        "company": "Straits Analytics",
        "location": "Tanjong Pagar, Singapore",
        "description": (
            "Develop Python data services, SQL and Postgres models, evaluation datasets, "
            "and monitored LLM workflows for enterprise products."
        ),
        "url": "https://example.com/jobs/data-ai-engineer",
    },
    {
        "title": "Product Engineer, Intelligent Workflows",
        "company": "RelayWorks",
        "location": "Singapore",
        "description": (
            "Build secure end-to-end product experiences with Next.js, TypeScript, Supabase, "
            "FastAPI, Playwright, and LLM-assisted workflows."
        ),
        "url": "https://example.com/jobs/product-engineer-intelligent-workflows",
    },
    {
        "title": "LLM Evaluation Engineer",
        "company": "Assure AI",
        "location": "Singapore / Remote",
        "description": (
            "Design pytest and Playwright evaluations, adversarial tests, model quality metrics, "
            "and governance controls for production LLM systems."
        ),
        "url": "https://example.com/jobs/llm-evaluation-engineer",
    },
    {
        "title": "Cloud Application Engineer",
        "company": "Cobalt Stack",
        "location": "Paya Lebar, Singapore",
        "description": (
            "Deliver React and FastAPI applications backed by Postgres, with secure APIs, "
            "automated testing, observability, and cloud deployment."
        ),
        "url": "https://example.com/jobs/cloud-application-engineer",
    },
    {
        "title": "Associate Software Engineer, AI Products",
        "company": "Launchpad Logic",
        "location": "Singapore",
        "description": (
            "Support TypeScript, React, Python, and SQL product development while learning "
            "LLM evaluation, security, and reliable delivery practices."
        ),
        "url": "https://example.com/jobs/associate-software-engineer-ai-products",
    },
]

_JOB_CACHE: TTLCache[tuple[list[JobPosting], str]] = TTLCache(max_size=128, ttl_seconds=10 * 60)


class JobSourceUnavailable(RuntimeError):
    pass


async def fetch_jobs(
    target_role: str,
    location: str,
    limit: int,
) -> tuple[list[JobPosting], str, bool]:
    cache_key = _job_cache_key(target_role=target_role, location=location, limit=limit)
    cached = _JOB_CACHE.get(cache_key)
    if cached is not None:
        jobs, source_mode = cached
        return [job.model_copy(deep=True) for job in jobs], source_mode, True

    if settings.adzuna_app_id and settings.adzuna_app_key:
        try:
            jobs = await _fetch_adzuna_jobs(target_role, location, limit)
            _require_jobs(jobs)
            source_mode = "adzuna"
        except Exception as exc:
            _log_provider_failure("adzuna", exc, "mycareersfuture_or_apify")
            jobs, source_mode = await _fetch_secondary_or_demo(target_role, location, limit)
    elif _is_singapore_location(location):
        try:
            jobs = await _fetch_mycareersfuture_jobs(target_role, limit)
            _require_jobs(jobs)
            source_mode = "mycareersfuture"
        except Exception as exc:
            _log_provider_failure("mycareersfuture", exc, "apify")
            jobs, source_mode = await _fetch_apify_or_demo(target_role, location, limit)
    elif settings.apify_mcf_run_url and settings.apify_api_token:
        try:
            jobs = await _fetch_apify_mycareersfuture_jobs(target_role, location, limit)
            source_mode = "apify_mycareersfuture"
        except Exception as exc:
            _log_provider_failure("apify_mycareersfuture", exc, "none")
            jobs, source_mode = _explicit_demo_or_raise(limit)
    else:
        jobs, source_mode = _explicit_demo_or_raise(limit)

    _JOB_CACHE.set(cache_key, ([job.model_copy(deep=True) for job in jobs], source_mode))
    return jobs, source_mode, False


async def _fetch_adzuna_jobs(target_role: str, location: str, limit: int) -> list[JobPosting]:
    url = f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "what": target_role,
        "where": location,
        "results_per_page": min(limit, settings.max_job_limit),
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(url, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
    payload = response.json()
    return [_normalize_adzuna_job(item) for item in payload.get("results", [])][:limit]


async def _fetch_secondary_or_demo(
    target_role: str,
    location: str,
    limit: int,
) -> tuple[list[JobPosting], str]:
    if _is_singapore_location(location):
        try:
            jobs = await _fetch_mycareersfuture_jobs(target_role, limit)
            _require_jobs(jobs)
            return jobs, "mycareersfuture_fallback"
        except Exception as exc:
            _log_provider_failure("mycareersfuture", exc, "apify")
    if settings.apify_mcf_run_url and settings.apify_api_token:
        try:
            return (
                await _fetch_apify_mycareersfuture_jobs(target_role, location, limit),
                "apify_mycareersfuture_fallback",
            )
        except Exception as exc:
            _log_provider_failure("apify_mycareersfuture", exc, "none")
    return _explicit_demo_or_raise(limit)


async def _fetch_apify_or_demo(
    target_role: str,
    location: str,
    limit: int,
) -> tuple[list[JobPosting], str]:
    if settings.apify_mcf_run_url and settings.apify_api_token:
        try:
            jobs = await _fetch_apify_mycareersfuture_jobs(target_role, location, limit)
            _require_jobs(jobs)
            return jobs, "apify_mycareersfuture_fallback"
        except Exception as exc:
            _log_provider_failure("apify_mycareersfuture", exc, "none")
    return _explicit_demo_or_raise(limit)


def _explicit_demo_or_raise(limit: int) -> tuple[list[JobPosting], str]:
    if settings.allow_demo_data:
        log_event("job_source_demo_used", reason="explicit_demo_configuration", job_limit=limit)
        return _demo_jobs(limit), "demo"
    raise JobSourceUnavailable(
        "No live job provider returned results. Demo data is disabled, "
        "so no roles were substituted."
    )


def _log_provider_failure(provider: str, exc: Exception, next_provider: str) -> None:
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
    log_event(
        "job_provider_failed",
        provider=provider,
        error_class=type(exc).__name__,
        status_code=status_code,
        next_provider=next_provider,
    )


async def _fetch_mycareersfuture_jobs(target_role: str, limit: int) -> list[JobPosting]:
    params = {
        "search": target_role,
        "limit": min(limit, settings.max_job_limit),
    }
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(
            "https://api.mycareersfuture.gov.sg/v2/jobs",
            params=params,
            headers={
                "Accept": "application/json",
                "User-Agent": "Resonant/0.1",
            },
        )
        response.raise_for_status()
    payload = response.json()
    items = payload.get("results", []) if isinstance(payload, dict) else []
    return [_normalize_mycareersfuture_job(item) for item in items if isinstance(item, dict)][
        :limit
    ]


async def _fetch_apify_mycareersfuture_jobs(
    target_role: str,
    location: str,
    limit: int,
) -> list[JobPosting]:
    url = _apify_sync_dataset_url(settings.apify_mcf_run_url)
    params = {
        "token": settings.apify_api_token,
        "timeout": 90,
        "memory": 512,
    }
    job_limit = min(limit, settings.max_job_limit)
    payload = {
        "searchQuery": target_role,
        "sector": "",
        "location": "" if _is_country_level_location(location) else location,
        "salaryMin": 0,
        "salaryMax": 0,
        "employmentType": "ALL",
        "seniorityLevel": "",
        "postedWithinDays": 30,
        "maxResults": job_limit,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            url,
            params=params,
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        response.raise_for_status()
    payload_json = response.json()
    items = payload_json if isinstance(payload_json, list) else payload_json.get("items", [])
    jobs = [_normalize_apify_mycareersfuture_job(item) for item in items if isinstance(item, dict)]
    return jobs[:limit]


def _apify_sync_dataset_url(run_url: str) -> str:
    base = run_url.split("?", 1)[0].rstrip("/")
    if base.endswith("/run-sync-get-dataset-items"):
        return base
    if base.endswith("/runs"):
        return f"{base.removesuffix('/runs')}/run-sync-get-dataset-items"
    return base


def _normalize_apify_mycareersfuture_job(item: dict[str, Any]) -> JobPosting:
    title = _first_text(item, "title", "jobTitle", "job_title") or "Untitled role"
    company = (
        _first_text(item, "company", "companyName", "employerName", "hiringCompany")
        or "Unknown company"
    )
    location = (
        _first_text(item, "location", "formattedLocation", "address", "district")
        or settings.apify_mcf_country
        or "Singapore"
    )
    raw_description = _first_text(
        item,
        "descriptionText",
        "descriptionMarkdown",
        "description",
        "descriptionHtml",
        "jobDescription",
    )
    description, _warnings = sanitize_untrusted_text(raw_description or "")
    url = _first_text(item, "url", "jobUrl", "job_url", "applyUrl") or _mycareersfuture_url(
        _first_text(item, "jobPostId", "job_post_id", "id", "jobId")
    )
    external_id = str(
        _first_text(item, "jobPostId", "job_post_id", "id", "jobId")
        or hashlib.sha256(f"{title}:{company}:{url}".encode()).hexdigest()
    )
    return JobPosting(
        external_id=external_id,
        title=title,
        company=company,
        location=location,
        description=_truncate(description, 2000),
        url=url,
        salary_min=_first_int(item, "salaryMin", "salary_min", "minSalary", "minimumSalary"),
        salary_max=_first_int(item, "salaryMax", "salary_max", "maxSalary", "maximumSalary"),
        source="apify_mycareersfuture",
    )


def _normalize_mycareersfuture_job(item: dict[str, Any]) -> JobPosting:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    company_info = item.get("company") if isinstance(item.get("company"), dict) else {}
    posted_company = (
        item.get("postedCompany") if isinstance(item.get("postedCompany"), dict) else {}
    )
    hiring_company = (
        item.get("hiringCompany") if isinstance(item.get("hiringCompany"), dict) else {}
    )
    salary = item.get("salary") if isinstance(item.get("salary"), dict) else {}
    address = item.get("address") if isinstance(item.get("address"), dict) else {}

    title = _first_text(item, "title") or "Untitled role"
    company = (
        _first_text(item, "company")
        or _first_text(hiring_company, "name")
        or _first_text(posted_company, "name")
        or _first_text(company_info, "name")
        or "Unknown company"
    )
    location = _format_mycareersfuture_location(address)
    description, _warnings = sanitize_untrusted_text(_first_text(item, "description"))
    job_id = _first_text(metadata, "jobPostId") or _first_text(item, "uuid")
    url = _first_text(metadata, "jobDetailsUrl") or _mycareersfuture_url(job_id)

    return JobPosting(
        external_id=job_id or hashlib.sha256(f"{title}:{company}:{url}".encode()).hexdigest(),
        title=title,
        company=company,
        location=location,
        description=_truncate(description, 2000),
        url=url,
        salary_min=_first_int(salary, "minimum"),
        salary_max=_first_int(salary, "maximum"),
        source="mycareersfuture",
    )


def _format_mycareersfuture_location(address: dict[str, Any]) -> str:
    if not address:
        return "Singapore"
    parts = [
        _first_text(address, "block"),
        _first_text(address, "street"),
        _first_text(address, "building"),
        _first_text(address, "postalCode"),
    ]
    location = ", ".join(part for part in parts if part)
    return location or "Singapore"


def _first_text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            parts = [str(part).strip() for part in value if str(part).strip()]
            if parts:
                return ", ".join(parts)
    return ""


def _first_int(item: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None


def _mycareersfuture_url(job_id: str | None) -> str:
    if not job_id:
        return "https://www.mycareersfuture.gov.sg/"
    return f"https://www.mycareersfuture.gov.sg/job/{job_id}"


def _is_country_level_location(location: str) -> bool:
    normalized = location.strip().lower()
    return normalized in {"singapore", "sg", "remote", "anywhere", "all"}


def _is_singapore_location(location: str) -> bool:
    normalized = location.strip().lower()
    return normalized in {"singapore", "sg"} or "singapore" in normalized


def _normalize_adzuna_job(item: dict[str, Any]) -> JobPosting:
    title = item.get("title") or "Untitled role"
    company = (item.get("company") or {}).get("display_name") or "Unknown company"
    location = (item.get("location") or {}).get("display_name") or "Unknown location"
    description, _warnings = sanitize_untrusted_text(item.get("description") or "")
    url = item.get("redirect_url") or "https://www.adzuna.com"
    external_id = str(
        item.get("id") or hashlib.sha256(f"{title}:{company}:{url}".encode()).hexdigest()
    )
    return JobPosting(
        external_id=external_id,
        title=title,
        company=company,
        location=location,
        description=_truncate(description, 2000),
        url=url,
        salary_min=item.get("salary_min"),
        salary_max=item.get("salary_max"),
        source="adzuna",
    )


def _demo_jobs(limit: int) -> list[JobPosting]:
    jobs: list[JobPosting] = []
    for item in DEMO_JOBS[:limit]:
        external_id = hashlib.sha256(f"{item['title']}:{item['company']}".encode()).hexdigest()[:16]
        cleaned, _warnings = sanitize_untrusted_text(item["description"])
        cleaned = _truncate(cleaned, 2000)
        jobs.append(
            JobPosting(external_id=external_id, source="demo", **{**item, "description": cleaned})
        )
    return jobs


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 3]}..."


def _require_jobs(jobs: list[JobPosting]) -> None:
    if not jobs:
        raise ValueError("Job provider returned no usable results")


def _job_cache_key(target_role: str, location: str, limit: int) -> str:
    if settings.adzuna_app_id and settings.adzuna_app_key:
        provider = "adzuna"
    elif _is_singapore_location(location):
        provider = "mycareersfuture"
    elif settings.apify_mcf_run_url and settings.apify_api_token:
        provider = "apify_mycareersfuture"
    else:
        provider = "demo"
    payload = (
        f"{provider}:{settings.adzuna_country}:{settings.apify_mcf_country}:"
        f"{target_role.lower()}:{location.lower()}:{limit}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
