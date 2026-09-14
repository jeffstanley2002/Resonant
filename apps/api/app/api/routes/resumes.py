from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.auth import AuthUser, require_user
from app.core.logging import log_event
from app.schemas import ResumeAnalysis
from app.services.ai_extraction import analyze_resume_text
from app.services.resume_parser import parse_upload
from app.services.storage import save_resume_analysis

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/analyze", response_model=ResumeAnalysis)
async def analyze_resume(
    file: UploadFile = File(...),
    user: AuthUser = Depends(require_user),
) -> ResumeAnalysis:
    parsed = await parse_upload(file)
    insights, telemetry, ai_stage = await analyze_resume_text(parsed.text)
    digest = hashlib.sha256(f"{user.id}:{parsed.text[:2000]}".encode()).hexdigest()[:16]
    analysis = ResumeAnalysis(
        resume_id=f"resume_{digest}",
        summary=insights.summary if insights else "",
        skills=(
            [
                {
                    "name": skill.name,
                    "category": skill.category,
                    "confidence": skill.confidence,
                }
                for skill in insights.skills
            ]
            if insights
            else []
        ),
        role_signals=insights.role_signals if insights else [],
        seniority=insights.seniority if insights else None,
        evidence=insights.evidence if insights else [],
        uncertainties=insights.uncertainties if insights else [],
        ai_status=ai_stage.status,
        warnings=[*parsed.warnings, *([ai_stage.message] if ai_stage.message else [])],
        mode=f"ai_{ai_stage.status}",
        telemetry={**telemetry, "storage_persisted": True},
    )
    try:
        await save_resume_analysis(user_id=user.id, resume_hash=digest, analysis=analysis)
    except Exception as exc:
        log_event(
            "resume_analysis_persistence_failed",
            error_class=type(exc).__name__,
            error_detail=str(exc)[:200],
        )
        analysis.telemetry["storage_persisted"] = False
        analysis.telemetry["storage_error_class"] = type(exc).__name__
        if insights:
            analysis.warnings.append(
                "Resume was analyzed, but saving failed. "
                "Matching will use extracted facts for this session."
            )
        else:
            analysis.warnings.append(
                "Resume analysis failed and saving also failed. "
                "Retry after the model provider is available."
            )
    return analysis
