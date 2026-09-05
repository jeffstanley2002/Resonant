from __future__ import annotations

import uuid
from typing import TypedDict

from app.core.config import settings
from app.core.logging import log_event
from app.schemas import (
    AIStageResult,
    JobMatch,
    JobPosting,
    MatchRequest,
    MatchResponse,
    ResumeAnalysis,
    Skill,
)
from app.services.ai_extraction import analyze_resume_text
from app.services.job_normalizer import normalize_jobs
from app.services.job_sources import JobSourceUnavailable, fetch_jobs
from app.services.match_reasoning import reason_about_matches
from app.services.ranking import synthesize_ranking
from app.services.scoring import score_jobs
from app.services.storage import get_resume_analysis, save_match_run


class ResumeAnalysisNotFound(Exception):
    pass


class MatchState(TypedDict, total=False):
    user_id: str
    request: MatchRequest
    run_id: str
    resume_analysis: ResumeAnalysis
    resume_text: str
    skills: list[Skill]
    resume_evidence: list[str]
    jobs: list[JobPosting]
    source_mode: str
    candidates: list[JobMatch]
    matches: list[JobMatch]
    stages: list[AIStageResult]
    warnings: list[str]
    telemetry: dict
    stopped: bool


async def run_match_workflow(user_id: str, request: MatchRequest) -> MatchResponse:
    safe_limit = min(request.limit, settings.max_job_limit)
    run_id = f"run_{uuid.uuid4().hex[:16]}"
    log_event("agent_run_started", run_id=run_id, user_id=user_id, limit=safe_limit)
    state: MatchState = {
        "user_id": user_id,
        "request": request.model_copy(update={"limit": safe_limit}),
        "run_id": run_id,
        "matches": [],
        "stages": [],
        "warnings": [],
        "telemetry": {"run_id": run_id},
        "stopped": False,
    }

    try:
        graph = _compile_graph()
    except Exception as exc:
        log_event("langgraph_unavailable", run_id=run_id, error_class=type(exc).__name__)
        state["stages"].append(
            AIStageResult(
                stage="orchestration",
                status="failed",
                message=(
                    "LangGraph orchestration is unavailable. No AI recommendations were generated."
                ),
            )
        )
        return _build_response(state)

    state = await graph.ainvoke(state)
    response = _build_response(state)
    log_event(
        "agent_run_completed",
        run_id=run_id,
        user_id=user_id,
        workflow_status=response.status,
        source_mode=response.mode,
        match_count=len(response.matches),
        model=response.telemetry.get("model"),
        provider=response.telemetry.get("provider"),
        estimated_cost_usd=response.telemetry.get("estimated_cost_usd"),
        model_fallback=response.telemetry.get("model_fallback"),
    )
    return response


def _compile_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(MatchState)
    graph.add_node("parse_resume", _parse_resume_node)
    graph.add_node("analyze_resume", _analyze_resume_node)
    graph.add_node("fetch_jobs", _fetch_jobs_node)
    graph.add_node("analyze_jobs", _analyze_jobs_node)
    graph.add_node("select_candidates", _select_candidates_node)
    graph.add_node("reason_matches", _reason_matches_node)
    graph.add_node("synthesize_ranking", _synthesize_ranking_node)
    graph.add_node("validate_output", _validate_output_node)
    graph.add_node("persist_results", _persist_results_node)
    graph.add_edge(START, "parse_resume")
    graph.add_edge("parse_resume", "analyze_resume")
    graph.add_edge("analyze_resume", "fetch_jobs")
    graph.add_edge("fetch_jobs", "analyze_jobs")
    graph.add_edge("analyze_jobs", "select_candidates")
    graph.add_edge("select_candidates", "reason_matches")
    graph.add_edge("reason_matches", "synthesize_ranking")
    graph.add_edge("synthesize_ranking", "validate_output")
    graph.add_edge("validate_output", "persist_results")
    graph.add_edge("persist_results", END)
    return graph.compile()


async def _parse_resume_node(state: MatchState) -> MatchState:
    request = state["request"]
    if request.resume_id:
        analysis = await get_resume_analysis(state["user_id"], request.resume_id)
        if analysis is None:
            raise ResumeAnalysisNotFound(request.resume_id)
        state["resume_analysis"] = analysis
        state["telemetry"]["resume_analysis_mode"] = analysis.mode
    elif request.resume_text:
        state["resume_text"] = request.resume_text
        state["telemetry"]["resume_analysis_mode"] = "inline"
    return state


async def _analyze_resume_node(state: MatchState) -> MatchState:
    if state["stopped"]:
        return state
    if "resume_analysis" in state:
        analysis = state["resume_analysis"]
        stage = AIStageResult(
            stage="resume_analysis",
            status=analysis.ai_status,
            message=(
                analysis.warnings[-1]
                if analysis.ai_status == "failed" and analysis.warnings
                else None
            ),
        )
        state["stages"].append(stage)
        if analysis.ai_status != "succeeded":
            state["stopped"] = True
            return state
        state["skills"] = analysis.skills
        state["resume_evidence"] = analysis.evidence
    else:
        insights, telemetry, stage = await analyze_resume_text(state["resume_text"])
        state["telemetry"].update(telemetry)
        state["stages"].append(stage)
        if insights is None:
            state["stopped"] = True
            return state
        state["skills"] = [
            Skill(name=skill.name, category=skill.category, confidence=skill.confidence)
            for skill in insights.skills
        ]
        state["resume_evidence"] = insights.evidence
    state["telemetry"]["skill_count"] = len(state["skills"])
    return state


async def _fetch_jobs_node(state: MatchState) -> MatchState:
    if state["stopped"]:
        return state
    request = state["request"]
    try:
        jobs, source_mode, cache_hit = await fetch_jobs(
            request.target_role, request.location, request.limit
        )
    except JobSourceUnavailable as exc:
        state["stages"].append(
            AIStageResult(stage="job_retrieval", status="failed", message=str(exc))
        )
        state["stopped"] = True
        return state
    state["jobs"] = jobs
    state["source_mode"] = source_mode
    state["telemetry"]["job_count"] = len(jobs)
    state["telemetry"]["job_cache_hit"] = cache_hit
    state["stages"].append(
        AIStageResult(
            stage="job_retrieval", status="succeeded", processed=len(jobs), total=len(jobs)
        )
    )
    return state


async def _analyze_jobs_node(state: MatchState) -> MatchState:
    if state["stopped"]:
        return state
    jobs, telemetry, stage = await normalize_jobs(state["jobs"])
    state["telemetry"].update(telemetry)
    state["stages"].append(stage)
    state["jobs"] = jobs
    if stage.status == "failed" or not jobs:
        state["stopped"] = True
    return state


async def _select_candidates_node(state: MatchState) -> MatchState:
    if state["stopped"]:
        return state
    state["candidates"] = score_jobs(
        state["skills"],
        state["jobs"],
        state.get("resume_evidence", []),
    )
    state["telemetry"]["ranker"] = "local-tfidf-semantic-ranker-v1"
    return state


async def _reason_matches_node(state: MatchState) -> MatchState:
    if state["stopped"]:
        return state
    matches, telemetry, stage = await reason_about_matches(
        state["candidates"], state["skills"], state.get("resume_evidence", [])
    )
    state["telemetry"].update(telemetry)
    state["stages"].append(stage)
    state["matches"] = matches
    if stage.status == "failed" or not matches:
        state["stopped"] = True
    return state


async def _synthesize_ranking_node(state: MatchState) -> MatchState:
    if state["stopped"]:
        return state
    if state["telemetry"].get("matching_degraded_to_baseline"):
        state["telemetry"]["ranking_skipped_reason"] = "baseline_match_reasoning"
        state["stages"].append(
            AIStageResult(
                stage="ranking_synthesis",
                status="skipped",
                message=(
                    "AI ranking synthesis was skipped because roles are already ordered "
                    "by baseline match score."
                ),
                processed=len(state["matches"]),
                total=len(state["matches"]),
            )
        )
        return state
    matches, telemetry, stage = await synthesize_ranking(state["matches"])
    state["telemetry"].update(telemetry)
    state["stages"].append(stage)
    state["matches"] = matches
    if stage.status == "failed" or not matches:
        state["stopped"] = True
    return state


async def _validate_output_node(state: MatchState) -> MatchState:
    if state["stopped"]:
        return state
    valid = [
        match
        for match in state["matches"]
        if match.ai_status in {"succeeded", "partial"}
        and match.explanation
        and match.job.required_skills is not None
    ]
    if len(valid) != len(state["matches"]):
        state["stages"].append(
            AIStageResult(
                stage="output_validation",
                status="partial" if valid else "failed",
                message=f"Validated {len(valid)} of {len(state['matches'])} AI recommendations.",
                processed=len(valid),
                total=len(state["matches"]),
            )
        )
    else:
        state["stages"].append(
            AIStageResult(
                stage="output_validation",
                status="succeeded",
                processed=len(valid),
                total=len(valid),
            )
        )
    state["matches"] = valid
    if not valid:
        state["stopped"] = True
    return state


async def _persist_results_node(state: MatchState) -> MatchState:
    if not state["matches"]:
        state["telemetry"]["persistence_status"] = "skipped"
        return state
    telemetry = _trim_telemetry(_finalize_telemetry(state["telemetry"]))
    try:
        await save_match_run(
            user_id=state["user_id"],
            run_id=state["run_id"],
            request=state["request"],
            source_mode=state.get("source_mode", "unavailable"),
            matches=state["matches"][: state["request"].limit],
            telemetry=telemetry,
        )
        state["telemetry"]["persistence_status"] = "saved"
    except Exception as exc:
        log_event(
            "agent_persistence_failed", run_id=state["run_id"], error_class=type(exc).__name__
        )
        state["telemetry"]["persistence_status"] = "failed"
        state["warnings"].append(
            "Results were generated, but persistence is temporarily unavailable."
        )
    return state


def _build_response(state: MatchState) -> MatchResponse:
    stages = state.get("stages", [])
    matches = state.get("matches", [])[: state["request"].limit]
    failed = [stage for stage in stages if stage.status == "failed"]
    partial = [stage for stage in stages if stage.status == "partial"]
    status = "failed" if not matches else ("partial" if failed or partial else "succeeded")
    telemetry = _trim_telemetry(_finalize_telemetry(state.get("telemetry", {})))
    telemetry["workflow_status"] = status
    return MatchResponse(
        run_id=state["run_id"],
        mode=state.get("source_mode", "unavailable"),
        matches=matches,
        status=status,
        stages=stages,
        error_message=failed[0].message if status == "failed" and failed else None,
        warnings=state.get("warnings", []),
        telemetry=telemetry,
    )


def _finalize_telemetry(telemetry: dict) -> dict:
    result = dict(telemetry)
    prefixes = ("extraction", "normalization", "matching", "ranking")
    result["estimated_cost_usd"] = round(
        sum(float(result.get(f"{prefix}_cost_usd") or 0) for prefix in prefixes)
        + float(result.get("estimated_cost_usd") or 0),
        8,
    )
    result["model_fallback"] = any(
        bool(result.get(f"{prefix}_fallback")) for prefix in prefixes
    ) or bool(result.get("model_fallback"))
    result["llm_attempts"] = sum(
        int(result.get(f"{prefix}_attempts") or 0) for prefix in prefixes
    ) + int(result.get("model_attempts") or 0)
    result["input_tokens"] = sum(
        int(result.get(f"{prefix}_input_tokens") or 0) for prefix in prefixes
    ) + int(result.get("model_input_tokens") or 0)
    result["output_tokens"] = sum(
        int(result.get(f"{prefix}_output_tokens") or 0) for prefix in prefixes
    ) + int(result.get("model_output_tokens") or 0)
    result["model"] = (
        result.get("ranking_model") or result.get("matching_model") or result.get("model")
    )
    result["provider"] = (
        result.get("ranking_provider") or result.get("matching_provider") or result.get("provider")
    )
    result["model_latency_ms"] = (
        result.get("ranking_latency_ms")
        or result.get("matching_latency_ms")
        or result.get("model_latency_ms")
    )
    return result


def _trim_telemetry(telemetry: dict) -> dict[str, str | int | float | bool | None]:
    exact = {
        "run_id",
        "resume_analysis_mode",
        "skill_count",
        "job_count",
        "ranker",
        "model",
        "provider",
        "model_latency_ms",
        "estimated_cost_usd",
        "model_fallback",
        "model_fallback_reason",
        "model_error_class",
        "model_attempts",
        "job_cache_hit",
        "persistence_status",
        "llm_attempts",
        "input_tokens",
        "output_tokens",
        "workflow_status",
    }
    safe_prefixes = ("extraction_", "normalization_", "matching_", "ranking_")
    return {
        key: value
        for key, value in telemetry.items()
        if key in exact or key.startswith(safe_prefixes)
    }
