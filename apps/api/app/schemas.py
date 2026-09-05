from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.services.sanitization import sanitize_untrusted_text


class Skill(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="general", max_length=40)
    confidence: float = Field(ge=0, le=1, default=0.7)


AIStatus = Literal["succeeded", "partial", "failed", "skipped"]


class AIStageResult(BaseModel):
    stage: str = Field(min_length=1, max_length=80)
    status: AIStatus
    message: str | None = Field(default=None, max_length=300)
    processed: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)


class ResumeAnalysis(BaseModel):
    resume_id: str
    summary: str = ""
    skills: list[Skill] = Field(default_factory=list)
    role_signals: list[str] = Field(default_factory=list, max_length=10)
    seniority: str | None = Field(default=None, max_length=80)
    evidence: list[str] = Field(default_factory=list, max_length=12)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    ai_status: AIStatus = "failed"
    warnings: list[str] = Field(default_factory=list)
    mode: str = "ai_required"
    telemetry: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class MatchRequest(BaseModel):
    resume_id: str | None = Field(default=None, pattern=r"^resume_[a-fA-F0-9]{8,64}$")
    resume_text: str | None = Field(default=None, min_length=20, max_length=80_000)
    target_role: str = Field(default="Software Engineer", min_length=2, max_length=120)
    location: str = Field(default="Singapore", min_length=2, max_length=120)
    limit: int = Field(default=30, ge=1, le=40)

    @field_validator("resume_text")
    @classmethod
    def sanitize_resume_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        sanitized, _warnings = sanitize_untrusted_text(value)
        if len(sanitized) < 20:
            raise ValueError("Resume text does not contain enough safe content")
        return sanitized

    @model_validator(mode="after")
    def require_resume_source(self) -> MatchRequest:
        if not self.resume_id and not self.resume_text:
            raise ValueError("Provide resume_id or resume_text")
        return self


class JobPosting(BaseModel):
    external_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=2000)
    url: HttpUrl | str
    salary_min: int | None = None
    salary_max: int | None = None
    source: str = "demo"
    required_skills: list[str] = Field(default_factory=list, max_length=20)
    preferred_skills: list[str] = Field(default_factory=list, max_length=20)
    seniority: str | None = Field(default=None, max_length=80)
    responsibilities: list[str] = Field(default_factory=list, max_length=10)
    domain_context: list[str] = Field(default_factory=list, max_length=10)
    risk_flags: list[str] = Field(default_factory=list, max_length=10)


class JobMatch(BaseModel):
    job: JobPosting
    fit_score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: str
    resume_evidence: list[str] = Field(default_factory=list, max_length=8)
    job_evidence: list[str] = Field(default_factory=list, max_length=8)
    concerns: list[str] = Field(default_factory=list, max_length=6)
    confidence: float = Field(default=0.5, ge=0, le=1)
    baseline_score: int | None = Field(default=None, ge=0, le=100)
    ai_status: AIStatus = "succeeded"


class MatchResponse(BaseModel):
    run_id: str
    mode: str
    matches: list[JobMatch]
    status: AIStatus = "failed"
    stages: list[AIStageResult] = Field(default_factory=list)
    error_message: str | None = Field(default=None, max_length=300)
    warnings: list[str] = Field(default_factory=list)
    telemetry: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SaveJobRequest(BaseModel):
    external_job_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    job_url: HttpUrl | str
    notes: str | None = Field(default=None, max_length=1000)


class SavedJob(BaseModel):
    external_job_id: str
    title: str
    company: str
    job_url: HttpUrl | str
    notes: str | None = None


class FeedbackRequest(BaseModel):
    run_id: str = Field(min_length=4, max_length=120)
    rating: int = Field(ge=1, le=5)
    reason: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    status: str = "accepted"


class DataDeletionResponse(BaseModel):
    status: str = "deleted"
    deleted_tables: list[str]
