from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.encryption import (
    ENCRYPTION_VERSION,
    decrypt_json,
    encrypt_json,
    encryption_configured,
)
from app.schemas import (
    FeedbackRequest,
    JobMatch,
    MatchRequest,
    ResumeAnalysis,
    SavedJob,
    SaveJobRequest,
)

_DEMO_SAVED_JOBS: dict[str, dict[str, SavedJob]] = {}
_DEMO_RESUME_ANALYSES: dict[str, dict[str, ResumeAnalysis]] = {}
USER_DATA_TABLES = [
    "resume_analyses",
    "job_matches",
    "job_searches",
    "saved_jobs",
    "feedback",
    "agent_runs",
]


def supabase_configured() -> bool:
    return bool(
        not settings.demo_auth and settings.supabase_url and settings.supabase_service_role_key
    )


def get_supabase_client():
    if not supabase_configured():
        return None
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


async def save_resume_analysis(user_id: str, resume_hash: str, analysis: ResumeAnalysis) -> None:
    client = get_supabase_client()
    if client is None:
        _DEMO_RESUME_ANALYSES.setdefault(user_id, {})[analysis.resume_id] = analysis.model_copy(
            deep=True
        )
        return
    client.table("resume_analyses").insert(
        _resume_analysis_row(user_id=user_id, resume_hash=resume_hash, analysis=analysis)
    ).execute()


async def get_resume_analysis(user_id: str, resume_id: str) -> ResumeAnalysis | None:
    client = get_supabase_client()
    if client is None:
        analysis = _DEMO_RESUME_ANALYSES.get(user_id, {}).get(resume_id)
        return analysis.model_copy(deep=True) if analysis else None

    resume_hash = resume_id.removeprefix("resume_")
    result = (
        client.table("resume_analyses")
        .select(
            "summary,skills,warnings,encrypted_payload,encryption_version,analysis_mode,telemetry"
        )
        .eq("user_id", user_id)
        .eq("resume_hash", resume_hash)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    payload = (
        decrypt_json(row["encrypted_payload"])
        if row.get("encrypted_payload")
        else {
            "summary": row.get("summary", ""),
            "skills": row.get("skills", []),
            "warnings": row.get("warnings", []),
        }
    )
    return ResumeAnalysis(
        resume_id=resume_id,
        summary=payload.get("summary", ""),
        skills=payload.get("skills", []),
        role_signals=payload.get("role_signals", []),
        seniority=payload.get("seniority"),
        evidence=payload.get("evidence", []),
        uncertainties=payload.get("uncertainties", []),
        ai_status=payload.get(
            "ai_status",
            "succeeded" if row.get("analysis_mode") == "ai_succeeded" else "failed",
        ),
        warnings=payload.get("warnings", []),
        mode=payload.get("mode", row.get("analysis_mode") or "ai_failed"),
        telemetry=payload.get("telemetry", row.get("telemetry") or {}),
    )


def _resume_analysis_row(
    user_id: str,
    resume_hash: str,
    analysis: ResumeAnalysis,
) -> dict[str, Any]:
    skills = [skill.model_dump() for skill in analysis.skills]
    row: dict[str, Any] = {
        "user_id": user_id,
        "resume_hash": resume_hash,
        "summary": analysis.summary,
        "skills": skills,
        "warnings": analysis.warnings,
        "analysis_mode": analysis.mode,
        "telemetry": analysis.telemetry,
        "encrypted_payload": None,
        "encryption_version": None,
    }
    if not encryption_configured():
        return row

    row["encrypted_payload"] = encrypt_json(
        {
            "summary": analysis.summary,
            "skills": skills,
            "role_signals": analysis.role_signals,
            "seniority": analysis.seniority,
            "evidence": analysis.evidence,
            "uncertainties": analysis.uncertainties,
            "ai_status": analysis.ai_status,
            "warnings": analysis.warnings,
            "mode": analysis.mode,
            "telemetry": analysis.telemetry,
        }
    )
    row["encryption_version"] = ENCRYPTION_VERSION
    row["summary"] = "[encrypted]"
    row["skills"] = []
    row["warnings"] = []
    return row


async def save_feedback(user_id: str, request: FeedbackRequest) -> None:
    client = get_supabase_client()
    if client is None:
        return
    client.table("feedback").insert(
        {
            "user_id": user_id,
            "run_id": request.run_id,
            "rating": request.rating,
            "reason": request.reason,
        }
    ).execute()


async def save_job(user_id: str, request: SaveJobRequest) -> SavedJob:
    saved = SavedJob(
        external_job_id=request.external_job_id,
        title=request.title,
        company=request.company,
        job_url=request.job_url,
        notes=request.notes,
    )
    client = get_supabase_client()
    if client is None:
        _DEMO_SAVED_JOBS.setdefault(user_id, {})[request.external_job_id] = saved
        return saved

    client.table("saved_jobs").upsert(
        {
            "user_id": user_id,
            "external_job_id": request.external_job_id,
            "title": request.title,
            "company": request.company,
            "job_url": str(request.job_url),
            "notes": request.notes,
        },
        on_conflict="user_id,external_job_id",
    ).execute()
    return saved


async def list_saved_jobs(user_id: str) -> list[SavedJob]:
    client = get_supabase_client()
    if client is None:
        return list(_DEMO_SAVED_JOBS.get(user_id, {}).values())

    result = (
        client.table("saved_jobs")
        .select("external_job_id,title,company,job_url,notes")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [SavedJob(**item) for item in result.data or []]


async def delete_user_data(user_id: str) -> list[str]:
    client = get_supabase_client()
    if client is None:
        _DEMO_SAVED_JOBS.pop(user_id, None)
        _DEMO_RESUME_ANALYSES.pop(user_id, None)
        return USER_DATA_TABLES.copy()

    for table in USER_DATA_TABLES:
        client.table(table).delete().eq("user_id", user_id).execute()
    return USER_DATA_TABLES.copy()


async def save_match_run(
    user_id: str,
    run_id: str,
    request: MatchRequest,
    source_mode: str,
    matches: list[JobMatch],
    telemetry: dict[str, str | int | float | bool | None],
) -> None:
    client = get_supabase_client()
    if client is None:
        return

    search = (
        client.table("job_searches")
        .insert(
            {
                "user_id": user_id,
                "target_role": request.target_role,
                "location": request.location,
                "source_mode": source_mode,
            }
        )
        .execute()
    )
    search_id = search.data[0]["id"]
    if matches:
        client.table("job_matches").insert(
            [
                {
                    "user_id": user_id,
                    "search_id": search_id,
                    "external_job_id": match.job.external_id,
                    "title": match.job.title,
                    "company": match.job.company,
                    "location": match.job.location,
                    "job_url": str(match.job.url),
                    "fit_score": match.fit_score,
                    "matched_skills": match.matched_skills,
                    "missing_skills": match.missing_skills,
                    "explanation": match.explanation,
                }
                for match in matches
            ]
        ).execute()

    client.table("agent_runs").insert(
        {
            "user_id": user_id,
            "run_id": run_id,
            "status": "completed",
            "model": telemetry.get("model"),
            "provider": telemetry.get("provider"),
            "estimated_cost_usd": telemetry.get("estimated_cost_usd") or 0,
            "latency_ms": telemetry.get("model_latency_ms"),
            "fallback_reason": (
                telemetry.get("model_fallback_reason")
                or telemetry.get("normalization_fallback_reason")
                or telemetry.get("extraction_fallback_reason")
            ),
            "metadata": {
                "source_mode": source_mode,
                "skill_count": telemetry.get("skill_count"),
                "job_count": telemetry.get("job_count"),
                "ranker": telemetry.get("ranker"),
                "llm_attempts": telemetry.get("llm_attempts"),
                "input_tokens": telemetry.get("input_tokens"),
                "output_tokens": telemetry.get("output_tokens"),
                "normalization_model": telemetry.get("normalization_model"),
            },
        }
    ).execute()
