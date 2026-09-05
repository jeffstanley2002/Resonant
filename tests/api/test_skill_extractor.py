from __future__ import annotations

from app.services.skill_extractor import extract_skills


def test_extract_skills_deduplicates_case_insensitive_hits() -> None:
    skills = extract_skills("Python python PYTHON and React")
    names = [skill.name for skill in skills]

    assert names.count("Python") == 1
    assert "React" in names
