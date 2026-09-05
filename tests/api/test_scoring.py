from __future__ import annotations

from app.schemas import JobPosting, Skill
from app.services.scoring import score_jobs


def test_score_jobs_orders_by_skill_overlap() -> None:
    skills = [Skill(name="Python"), Skill(name="React"), Skill(name="Supabase")]
    jobs = [
        JobPosting(
            external_id="a",
            title="Office Coordinator",
            company="AdminCo",
            location="Remote",
            description="Scheduling and vendor coordination.",
            url="https://example.com/a",
        ),
        JobPosting(
            external_id="b",
            title="Full Stack Engineer",
            company="BuildCo",
            location="Remote",
            description="Python React Supabase application work.",
            url="https://example.com/b",
        ),
    ]

    ranked = score_jobs(skills, jobs)

    assert ranked[0].job.external_id == "b"
    assert ranked[0].fit_score > ranked[1].fit_score


def test_score_jobs_uses_lightweight_semantic_similarity() -> None:
    skills = [Skill(name="Machine learning"), Skill(name="Model evaluation")]
    evidence = ["Built ranking experiments for language model retrieval quality."]
    jobs = [
        JobPosting(
            external_id="admin",
            title="Operations Assistant",
            company="OfficeCo",
            location="Singapore",
            description="Coordinate rosters, invoices, calendars, and supplier paperwork.",
            url="https://example.com/admin",
        ),
        JobPosting(
            external_id="ml",
            title="AI Search Engineer",
            company="VectorCo",
            location="Singapore",
            description=(
                "Build machine learning ranking experiments for retrieval quality, "
                "model evaluation, and search relevance."
            ),
            url="https://example.com/ml",
        ),
    ]

    ranked = score_jobs(skills, jobs, evidence)

    assert ranked[0].job.external_id == "ml"
    assert ranked[0].fit_score > ranked[1].fit_score
