from __future__ import annotations

import hashlib
import re

from app.core.cache import TTLCache
from app.schemas import Skill

SKILL_CATALOG: dict[str, str] = {
    "python": "backend",
    "typescript": "frontend",
    "javascript": "frontend",
    "react": "frontend",
    "next.js": "frontend",
    "nextjs": "frontend",
    "fastapi": "backend",
    "django": "backend",
    "postgres": "database",
    "postgresql": "database",
    "supabase": "database",
    "sql": "database",
    "langgraph": "ai",
    "langchain": "ai",
    "llm": "ai",
    "rag": "ai",
    "machine learning": "ai",
    "docker": "devops",
    "aws": "cloud",
    "gcp": "cloud",
    "azure": "cloud",
    "vercel": "cloud",
    "render": "cloud",
    "pytest": "testing",
    "playwright": "testing",
    "security": "security",
    "oauth": "security",
    "api": "backend",
    "data analysis": "analytics",
    "excel": "analytics",
    "tableau": "analytics",
    "power bi": "analytics",
    "project management": "operations",
    "stakeholder management": "operations",
    "customer service": "service",
    "sales": "commercial",
    "marketing": "commercial",
    "seo": "commercial",
    "content strategy": "commercial",
    "accounting": "finance",
    "financial analysis": "finance",
    "operations": "operations",
    "communication": "general",
}

_SKILL_CACHE: TTLCache[list[Skill]] = TTLCache(max_size=256, ttl_seconds=30 * 60)


def extract_skills(text: str) -> list[Skill]:
    cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cached = _SKILL_CACHE.get(cache_key)
    if cached is not None:
        return [skill.model_copy() for skill in cached]

    normalized = text.lower()
    found: list[Skill] = []
    for skill, category in SKILL_CATALOG.items():
        pattern = rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])"
        if re.search(pattern, normalized):
            found.append(Skill(name=_display_name(skill), category=category, confidence=0.82))

    if not found:
        found.append(Skill(name="Communication", category="general", confidence=0.45))

    skills = dedupe_skills(found)
    _SKILL_CACHE.set(cache_key, [skill.model_copy() for skill in skills])
    return skills


def dedupe_skills(skills: list[Skill]) -> list[Skill]:
    seen: set[str] = set()
    result: list[Skill] = []
    for skill in skills:
        key = skill.name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(skill)
    return result


def _display_name(skill: str) -> str:
    names = {
        "nextjs": "Next.js",
        "next.js": "Next.js",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
        "fastapi": "FastAPI",
        "langgraph": "LangGraph",
        "langchain": "LangChain",
        "postgres": "Postgres",
        "postgresql": "PostgreSQL",
        "supabase": "Supabase",
        "playwright": "Playwright",
        "pytest": "Pytest",
        "llm": "LLM",
        "rag": "RAG",
        "api": "API",
        "sql": "SQL",
        "aws": "AWS",
        "gcp": "GCP",
        "seo": "SEO",
    }
    return names.get(skill, skill.title())
