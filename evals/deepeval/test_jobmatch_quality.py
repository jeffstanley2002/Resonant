from __future__ import annotations

import json
import pathlib

from app.schemas import JobPosting, Skill
from app.services.scoring import score_jobs
from app.services.skill_extractor import extract_skills
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class GroundedSkillMetric(BaseMetric):
    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.async_mode = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        output = json.loads(test_case.actual_output or "{}")
        evidence = " ".join(test_case.context or []).lower()
        claims = output.get("matched_skills", [])
        grounded = [claim for claim in claims if str(claim).lower() in evidence]
        self.score = len(grounded) / len(claims) if claims else 1.0
        self.reason = f"{len(grounded)} of {len(claims)} matched-skill claims have source evidence"
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case, *args, **kwargs)

    @property
    def __name__(self) -> str:
        return "Grounded Skill Claims"


def test_deepeval_skill_claims_are_grounded_in_resume_evidence() -> None:
    resume = "Python FastAPI Postgres LangGraph Playwright engineering projects"
    match = _rank_sample(resume)[0]
    case = LLMTestCase(
        input="Rank the sample roles",
        actual_output=json.dumps(match.model_dump(mode="json")),
        context=[resume],
        name="grounded-match-explanation",
        tags=["hallucination", "groundedness"],
    )
    metric = GroundedSkillMetric()

    assert metric.measure(case) == 1.0
    assert metric.is_successful() is True


def test_rule_based_baseline_never_fabricates_ai_explanation() -> None:
    matches = _rank_sample("Python FastAPI Postgres LangGraph engineering projects")
    assert matches[0].job.external_id == "relevant"
    assert matches[0].fit_score > matches[1].fit_score
    assert matches[0].explanation == ""
    assert matches[0].ai_status == "skipped"


def test_deepeval_extractor_does_not_invent_unrelated_skills() -> None:
    names = {skill.name for skill in extract_skills("Python FastAPI Postgres LangGraph Playwright")}

    assert {"Python", "FastAPI", "Postgres", "LangGraph", "Playwright"}.issubset(names)
    assert "Kubernetes" not in names


def test_deepeval_ranking_dataset_covers_five_candidate_profiles() -> None:
    dataset_path = pathlib.Path(__file__).parents[1] / "datasets" / "ranking_cases.json"
    cases = json.loads(dataset_path.read_text())

    assert len(cases) >= 5
    for case in cases:
        skills = extract_skills(case["resume"])
        relevant = JobPosting(
            external_id=f"{case['name']}_relevant",
            company="Relevant Co",
            location="Singapore",
            url="https://example.com/relevant",
            required_skills=[
                skill.name for skill in extract_skills(case["relevant"]["description"])
            ],
            **case["relevant"],
        )
        irrelevant = JobPosting(
            external_id=f"{case['name']}_irrelevant",
            company="Other Co",
            location="Singapore",
            url="https://example.com/irrelevant",
            required_skills=[
                skill.name for skill in extract_skills(case["irrelevant"]["description"])
            ],
            **case["irrelevant"],
        )

        ranked = score_jobs(skills, [irrelevant, relevant])

        assert ranked[0].job.external_id == relevant.external_id, case["name"]


def _rank_sample(resume: str):
    skills = [Skill(name=skill.name) for skill in extract_skills(resume)]
    jobs = [
        JobPosting(
            external_id="irrelevant",
            title="Retail Associate",
            company="ShopCo",
            location="Singapore",
            description="Customer service and store operations.",
            url="https://example.com/retail",
        ),
        JobPosting(
            external_id="relevant",
            title="AI Backend Engineer",
            company="AICo",
            location="Singapore",
            description="Build Python FastAPI Postgres LangGraph services.",
            url="https://example.com/ai",
        ),
    ]
    return score_jobs(skills, jobs)
