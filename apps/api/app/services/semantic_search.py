from __future__ import annotations

import math
import re
from collections import Counter

from app.schemas import JobPosting, Skill

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9.+#-]*")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def semantic_similarity_score(
    skills: list[Skill],
    job: JobPosting,
    resume_evidence: list[str] | None = None,
) -> float:
    """Return deterministic local TF-IDF cosine similarity in the 0..1 range."""
    resume_text = " ".join(
        [skill.name for skill in skills]
        + [skill.category for skill in skills]
        + (resume_evidence or [])
    )
    job_text = " ".join(
        [
            job.title,
            job.company,
            job.location,
            job.description,
            " ".join(job.required_skills),
            " ".join(job.preferred_skills),
            " ".join(job.responsibilities),
            " ".join(job.domain_context),
        ]
    )
    return _cosine_similarity(_tfidf(resume_text, job_text), _tfidf(job_text, resume_text))


def _tfidf(text: str, other_text: str) -> dict[str, float]:
    counts = Counter(_tokenize(text))
    if not counts:
        return {}
    other_tokens = set(_tokenize(other_text))
    total = sum(counts.values())
    vector: dict[str, float] = {}
    for token, count in counts.items():
        documents_containing_token = 1 + int(token in other_tokens)
        idf = math.log((1 + 2) / (1 + documents_containing_token)) + 1
        vector[token] = (count / total) * idf
    return vector


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    dot_product = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, dot_product / (left_norm * right_norm)))


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in (match.group(0).strip(".+-").lower() for match in TOKEN_PATTERN.finditer(text))
        if token and token not in STOP_WORDS
    ]
