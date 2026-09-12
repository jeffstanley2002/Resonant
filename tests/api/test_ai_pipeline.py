from __future__ import annotations

import asyncio
import json

from app.schemas import JobPosting
from app.services.agent import _compile_graph
from app.services.ai_extraction import (
    _RESUME_AI_CACHE,
    analyze_resume_text,
    build_extraction_prompt,
    extract_resume_skills,
)
from app.services.job_normalizer import (
    NORMALIZATION_BATCH_SIZE,
    JobRequirements,
    build_normalization_prompt,
    normalize_jobs,
)
from app.services.match_reasoning import reason_about_matches
from app.services.model_router import ModelResult
from app.services.ranking import synthesize_ranking
from app.services.scoring import score_jobs


class FakeRouter:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses

    async def complete(self, task: str, prompt: str) -> ModelResult:
        return ModelResult(
            content=self.responses[task],
            model="test/model",
            provider="test",
            latency_ms=2,
            estimated_cost_usd=0.0001,
            fallback=False,
            attempts=1,
            input_tokens=20,
            output_tokens=8,
        )


def test_model_skill_extraction_accepts_only_resume_grounded_skills(monkeypatch) -> None:
    router = FakeRouter(
        {
            "extract": (
                '{"summary": "Built grounded platform services with Kubernetes and Python.", '
                '"role_signals": ["Platform Engineer"], "seniority": null, '
                '"skills": [{"name": "Kubernetes", "category": "devops"}, '
                '{"name": "Terraform", "category": "devops"}], '
                '"evidence": ["Kubernetes"], "uncertainties": ["Seniority is not stated"]}'
            )
        }
    )
    monkeypatch.setattr("app.services.ai_extraction.model_router", router)

    skills, telemetry, warnings = asyncio.run(
        extract_resume_skills("Built Kubernetes services with Python and FastAPI.")
    )

    names = {skill.name for skill in skills}
    assert "Kubernetes" in names
    assert "Terraform" not in names
    assert telemetry["extraction_model"] == "test/model"
    assert warnings == []


def test_model_job_normalization_preserves_identity_and_rejects_invented_requirements(
    monkeypatch,
) -> None:
    router = FakeRouter(
        {
            "normalize": (
                '{"jobs": [{"external_id": "job_1", "required_skills": ["Kubernetes", "Rust"]}]}'
            )
        }
    )
    monkeypatch.setattr("app.services.job_normalizer.model_router", router)
    job = JobPosting(
        external_id="job_1",
        title="Platform Engineer",
        company="Example",
        location="Singapore",
        description="Operate Kubernetes platforms with Python.",
        url="https://example.com/job",
    )

    jobs, telemetry, stage = asyncio.run(normalize_jobs([job]))

    assert jobs[0].external_id == "job_1"
    assert jobs[0].company == "Example"
    assert "Kubernetes" in jobs[0].required_skills
    assert "Rust" not in jobs[0].required_skills
    assert telemetry["normalization_fallback"] is False
    assert stage.status == "succeeded"


def test_job_requirements_accepts_singleton_string_arrays() -> None:
    requirements = JobRequirements.model_validate(
        {
            "external_id": "job_1",
            "domain_context": "Software engineering",
            "risk_flags": "Requirements are ambiguous",
        }
    )

    assert requirements.domain_context == ["Software engineering"]
    assert requirements.risk_flags == ["Requirements are ambiguous"]


def test_normalization_prompt_specifies_array_fields() -> None:
    job = JobPosting(
        external_id="job_1",
        title="Python Engineer",
        company="Example",
        location="Singapore",
        description="Build Python services.",
        url="https://example.com/jobs/1",
    )

    prompt = build_normalization_prompt([job])

    assert '"output_schema"' in prompt
    assert '"domain_context": ["domain string"]' in prompt


def test_job_normalization_batches_large_inputs(monkeypatch) -> None:
    prompts: list[str] = []

    class BatchRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            prompts.append(prompt)
            ids = [job.external_id for job in jobs if job.external_id in prompt]
            payload = '{"jobs":[' + ",".join(
                f'{{"external_id":"{external_id}","required_skills":["Python"]}}'
                for external_id in ids
            ) + "]}"
            return ModelResult(
                content=payload,
                model="test/model",
                provider="test",
                latency_ms=2,
                estimated_cost_usd=0.0001,
                fallback=False,
                attempts=1,
            )

    jobs = [
        JobPosting(
            external_id=f"job_{index}",
            title="Python Engineer",
            company="Example",
            location="Singapore",
            description="Build Python services.",
            url=f"https://example.com/jobs/{index}",
        )
        for index in range(9)
    ]
    monkeypatch.setattr("app.services.job_normalizer.model_router", BatchRouter())

    normalized, telemetry, stage = asyncio.run(normalize_jobs(jobs))

    assert len(prompts) == 3
    assert all(
        len(json.loads(prompt)["jobs"]) <= NORMALIZATION_BATCH_SIZE for prompt in prompts
    )
    assert len(normalized) == 9
    assert telemetry["normalization_batch_count"] == 3
    assert telemetry["normalization_attempts"] == 3
    assert stage.status == "succeeded"


def test_job_normalization_keeps_successful_batches(monkeypatch) -> None:
    calls = 0

    class PartialRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            nonlocal calls
            calls += 1
            if calls == 2:
                return ModelResult(
                    content="",
                    model="unavailable",
                    provider="none",
                    latency_ms=16_000,
                    estimated_cost_usd=0,
                    fallback=True,
                    fallback_reason="provider_error",
                    error_class="TimeoutError",
                    attempts=2,
                )
            return ModelResult(
                content=(
                    '{"jobs":[{"external_id":"job_0",'
                    '"required_skills":["Python"]}]}'
                ),
                model="test/model",
                provider="test",
                latency_ms=2,
                estimated_cost_usd=0.0001,
                fallback=False,
                attempts=1,
            )

    jobs = [
        JobPosting(
            external_id=f"job_{index}",
            title="Python Engineer",
            company="Example",
            location="Singapore",
            description="Build Python services.",
            url=f"https://example.com/jobs/{index}",
        )
        for index in range(5)
    ]
    monkeypatch.setattr("app.services.job_normalizer.model_router", PartialRouter())

    normalized, telemetry, stage = asyncio.run(normalize_jobs(jobs))

    assert [job.external_id for job in normalized] == ["job_0"]
    assert telemetry["normalization_failed_batches"] == 1
    assert telemetry["normalization_fallback"] is True
    assert stage.status == "partial"
    assert stage.processed == 1


def test_failed_model_extraction_returns_no_deterministic_replacement(monkeypatch) -> None:
    router = FakeRouter({"extract": "not-json"})
    monkeypatch.setattr("app.services.ai_extraction.model_router", router)

    skills, telemetry, warnings = asyncio.run(
        extract_resume_skills("Python FastAPI Kubernetes engineering work.")
    )

    assert skills == []
    assert telemetry["extraction_validation_failed"] is True
    assert warnings == [
        "The model returned an invalid resume analysis. No AI resume facts were used."
    ]


def test_extraction_prompt_requires_structured_skill_objects() -> None:
    prompt = build_extraction_prompt("Python FastAPI engineering work.")

    assert "skills must be objects" in prompt
    assert '"output_schema"' in prompt
    assert '"name": "Python"' in prompt


def test_model_extraction_accepts_string_skills_and_caches_result(monkeypatch) -> None:
    _RESUME_AI_CACHE.clear()
    calls = 0

    class StringSkillRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            nonlocal calls
            calls += 1
            assert task == "extract"
            return ModelResult(
                content=(
                    '{"summary": "", "role_signals": "Backend Engineer", '
                    '"seniority": null, "skills": ["Python", "FastAPI"], '
                    '"evidence": "Python FastAPI", "uncertainties": null}'
                ),
                model="test/model",
                provider="test",
                latency_ms=2,
                estimated_cost_usd=0.001,
                fallback=False,
                attempts=1,
                input_tokens=100,
                output_tokens=50,
            )

    monkeypatch.setattr("app.services.ai_extraction.model_router", StringSkillRouter())

    first, first_telemetry, first_stage = asyncio.run(
        analyze_resume_text("Python FastAPI backend engineering work.")
    )
    second, second_telemetry, second_stage = asyncio.run(
        analyze_resume_text("Python FastAPI backend engineering work.")
    )

    assert calls == 1
    assert first_stage.status == "succeeded"
    assert second_stage.status == "succeeded"
    assert [skill.name for skill in first.skills] == ["Python", "FastAPI"]
    assert second.summary == first.summary
    assert first_telemetry["extraction_cache_hit"] is False
    assert second_telemetry["extraction_cache_hit"] is True
    assert second_telemetry["extraction_cost_usd"] == 0


def test_langgraph_contains_the_documented_ai_lifecycle() -> None:
    graph = _compile_graph().get_graph()

    assert {
        "parse_resume",
        "analyze_resume",
        "fetch_jobs",
        "analyze_jobs",
        "select_candidates",
        "reason_matches",
        "synthesize_ranking",
        "validate_output",
        "persist_results",
    }.issubset(graph.nodes)
    assert "generate_coaching" not in graph.nodes


def test_match_reasoning_timeout_returns_partial_baseline_matches(monkeypatch) -> None:
    class TimeoutRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            assert task == "match"
            return ModelResult(
                content="",
                model="unavailable",
                provider="none",
                latency_ms=48_000,
                estimated_cost_usd=0,
                fallback=True,
                fallback_reason="provider_error",
                error_class="TimeoutError",
                attempts=2,
            )

    monkeypatch.setattr("app.services.match_reasoning.model_router", TimeoutRouter())
    matches = score_jobs(
        skills=sample_skills(),
        jobs=[
            JobPosting(
                external_id="job_1",
                title="AI Backend Engineer",
                company="SignalWorks",
                location="Singapore",
                description="Build Python FastAPI LangGraph services.",
                url="https://example.com/job",
                required_skills=["Python", "FastAPI", "LangGraph"],
            )
        ],
    )

    reasoned, telemetry, stage = asyncio.run(
        reason_about_matches(matches, sample_skills(), ["Python FastAPI LangGraph"])
    )

    assert stage.status == "partial"
    assert reasoned[0].ai_status == "partial"
    assert reasoned[0].explanation.startswith("Baseline match")
    assert telemetry["matching_degraded_to_baseline"] is True


def test_invalid_match_reasoning_returns_partial_baseline_matches(monkeypatch) -> None:
    class InvalidRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            assert task == "match"
            return ModelResult(
                content='{"jobs": []}',
                model="test/model",
                provider="test",
                latency_ms=2,
                estimated_cost_usd=0.001,
                fallback=False,
                attempts=1,
            )

    monkeypatch.setattr("app.services.match_reasoning.model_router", InvalidRouter())
    matches = score_jobs(
        skills=sample_skills(),
        jobs=[
            JobPosting(
                external_id="job_1",
                title="AI Backend Engineer",
                company="SignalWorks",
                location="Singapore",
                description="Build Python FastAPI LangGraph services.",
                url="https://example.com/job",
                required_skills=["Python", "FastAPI", "LangGraph"],
            )
        ],
    )

    reasoned, telemetry, stage = asyncio.run(
        reason_about_matches(matches, sample_skills(), ["Python FastAPI LangGraph"])
    )

    assert stage.status == "partial"
    assert reasoned[0].ai_status == "partial"
    assert "invalid match reasoning" in (stage.message or "")
    assert telemetry["matching_validation_failed"] is True
    assert telemetry["matching_degraded_to_baseline"] is True


def test_ranking_timeout_preserves_existing_order(monkeypatch) -> None:
    class TimeoutRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            assert task == "rank"
            return ModelResult(
                content="",
                model="unavailable",
                provider="none",
                latency_ms=48_000,
                estimated_cost_usd=0,
                fallback=True,
                fallback_reason="provider_error",
                error_class="TimeoutError",
                attempts=2,
            )

    monkeypatch.setattr("app.services.ranking.model_router", TimeoutRouter())
    matches = score_jobs(
        skills=sample_skills(),
        jobs=[
            JobPosting(
                external_id="job_1",
                title="AI Backend Engineer",
                company="SignalWorks",
                location="Singapore",
                description="Build Python FastAPI LangGraph services.",
                url="https://example.com/job",
                required_skills=["Python", "FastAPI", "LangGraph"],
            )
        ],
    )

    ranked, telemetry, stage = asyncio.run(synthesize_ranking(matches))

    assert stage.status == "partial"
    assert ranked == matches
    assert telemetry["ranking_degraded_to_baseline"] is True


def test_invalid_ranking_preserves_existing_order(monkeypatch) -> None:
    class InvalidRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            assert task == "rank"
            return ModelResult(
                content="{not valid json",
                model="test/model",
                provider="test",
                latency_ms=2,
                estimated_cost_usd=0.001,
                fallback=False,
                attempts=1,
            )

    monkeypatch.setattr("app.services.ranking.model_router", InvalidRouter())
    matches = score_jobs(
        skills=sample_skills(),
        jobs=[
            JobPosting(
                external_id="job_1",
                title="AI Backend Engineer",
                company="SignalWorks",
                location="Singapore",
                description="Build Python FastAPI LangGraph services.",
                url="https://example.com/job",
                required_skills=["Python", "FastAPI", "LangGraph"],
            )
        ],
    )

    ranked, telemetry, stage = asyncio.run(synthesize_ranking(matches))

    assert stage.status == "partial"
    assert ranked == matches
    assert telemetry["ranking_validation_failed"] is True
    assert telemetry["ranking_degraded_to_baseline"] is True


def test_ranking_identity_mismatch_preserves_existing_order(monkeypatch) -> None:
    class MismatchRouter:
        async def complete(self, task: str, prompt: str) -> ModelResult:
            assert task == "rank"
            return ModelResult(
                content='{"ordered_external_ids": ["not_a_real_job"]}',
                model="test/model",
                provider="test",
                latency_ms=2,
                estimated_cost_usd=0.001,
                fallback=False,
                attempts=1,
            )

    monkeypatch.setattr("app.services.ranking.model_router", MismatchRouter())
    matches = score_jobs(
        skills=sample_skills(),
        jobs=[
            JobPosting(
                external_id="job_1",
                title="AI Backend Engineer",
                company="SignalWorks",
                location="Singapore",
                description="Build Python FastAPI LangGraph services.",
                url="https://example.com/job",
                required_skills=["Python", "FastAPI", "LangGraph"],
            )
        ],
    )

    ranked, telemetry, stage = asyncio.run(synthesize_ranking(matches))

    assert stage.status == "partial"
    assert ranked == matches
    assert telemetry["ranking_identity_validation_failed"] is True
    assert telemetry["ranking_degraded_to_baseline"] is True


def sample_skills():
    from app.schemas import Skill

    return [Skill(name="Python"), Skill(name="FastAPI"), Skill(name="LangGraph")]
