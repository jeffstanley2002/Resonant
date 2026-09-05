from __future__ import annotations

import re

from app.schemas import JobMatch, JobPosting, Skill
from app.services.semantic_search import semantic_similarity_score

IMPORTANT_SKILLS = [
    "python",
    "typescript",
    "react",
    "next.js",
    "fastapi",
    "postgres",
    "supabase",
    "langgraph",
    "llm",
    "security",
    "playwright",
    "pytest",
]


def score_jobs(
    skills: list[Skill], jobs: list[JobPosting], resume_evidence: list[str] | None = None
) -> list[JobMatch]:
    candidate_skills = {skill.name.lower(): skill.name for skill in skills}
    matches = [score_single_job(candidate_skills, job, skills, resume_evidence) for job in jobs]
    return sorted(matches, key=lambda match: match.fit_score, reverse=True)


def score_single_job(
    candidate_skills: dict[str, str],
    job: JobPosting,
    skills: list[Skill],
    resume_evidence: list[str] | None = None,
) -> JobMatch:
    job_text = f"{job.title} {job.description}".lower()
    matched: list[str] = []
    missing: list[str] = []

    requirements = job.required_skills or [
        _display(skill) for skill in IMPORTANT_SKILLS if _contains_skill(job_text, skill)
    ]
    normalized_candidates = {
        _canonical_skill(name): display_name for name, display_name in candidate_skills.items()
    }
    for requirement in requirements:
        skill = _canonical_skill(requirement)
        has_skill = skill in normalized_candidates
        if has_skill:
            matched.append(normalized_candidates[skill])
        elif not has_skill:
            missing.append(requirement)

    matched = list(dict.fromkeys(matched))
    missing = list(dict.fromkeys(missing))

    overlap_score = min(95, 45 + len(matched) * 9 - len(missing) * 4)
    ai_skills = ("langgraph", "llm", "python")
    if "ai" in job.title.lower() and any(skill in candidate_skills for skill in ai_skills):
        overlap_score += 6
    overlap_score = max(20, min(100, overlap_score))

    semantic_score = round(semantic_similarity_score(skills, job, resume_evidence) * 100)
    score = max(20, min(100, round(overlap_score * 0.8 + semantic_score * 0.2)))

    return JobMatch(
        job=job,
        fit_score=score,
        matched_skills=matched,
        missing_skills=missing[:6],
        explanation="",
        baseline_score=score,
        ai_status="skipped",
    )


def _contains_skill(text: str, skill: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", text))


def _display(skill: str) -> str:
    return {
        "llm": "LLM",
        "next.js": "Next.js",
    }.get(skill, skill.title())


def _canonical_skill(skill: str) -> str:
    normalized = skill.strip().lower().replace("postgresql", "postgres")
    return {"nextjs": "next.js", "large language models": "llm"}.get(normalized, normalized)
