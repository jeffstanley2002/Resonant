from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import log_event


@dataclass(frozen=True)
class ModelResult:
    content: str
    model: str
    provider: str
    latency_ms: float
    estimated_cost_usd: float
    fallback: bool
    fallback_reason: str | None = None
    error_class: str | None = None
    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ModelRouter:
    """Cost-aware provider routing with explicit failure results."""

    async def complete(self, task: str, prompt: str) -> ModelResult:
        start = time.perf_counter()
        errors: list[Exception] = []
        attempts = 0
        call_timeout = max(0.05, float(settings.model_call_timeout_seconds))
        budget = max(call_timeout, float(settings.model_task_budget_seconds))
        for model in self._candidate_models(task):
            for retry in range(2):
                remaining = budget - (time.perf_counter() - start)
                # Only start an attempt the budget can carry for a full call timeout.
                # A truncated slice is guaranteed to time out and just burns the budget
                # that the next candidate model needs.
                if remaining < call_timeout:
                    break
                attempts += 1
                attempt_started = time.perf_counter()
                try:
                    result = await asyncio.wait_for(
                        self._litellm_complete(task, prompt, model, start),
                        timeout=call_timeout,
                    )
                    return ModelResult(**{**result.__dict__, "attempts": attempts})
                except Exception as exc:
                    errors.append(exc)
                    # Distinguish our own deadline from a fast provider-side error:
                    # both surface as TimeoutError, but re-running a call that already
                    # exhausted the deadline will only exhaust it again.
                    deadline_exhausted = isinstance(exc, TimeoutError) and (
                        time.perf_counter() - attempt_started >= call_timeout - 0.5
                    )
                    log_event(
                        "model_provider_attempt_failed",
                        task=task,
                        model=model,
                        provider=self._provider_for_model(model),
                        attempt=attempts,
                        error_class=type(exc).__name__,
                        status_code=getattr(exc, "status_code", None),
                        deadline_exhausted=deadline_exhausted,
                    )
                    if retry == 0 and self._is_transient_error(exc) and not deadline_exhausted:
                        await asyncio.sleep(0.05)
                        continue
                    break

        last_error = errors[-1] if errors else None
        return ModelResult(
            content="",
            model="unavailable",
            provider="none",
            latency_ms=(time.perf_counter() - start) * 1000,
            estimated_cost_usd=0.0,
            fallback=True,
            fallback_reason="provider_error" if last_error else "provider_not_configured",
            error_class=type(last_error).__name__ if last_error else None,
            attempts=attempts,
        )

    async def _litellm_complete(
        self,
        task: str,
        prompt: str,
        model: str,
        start: float,
    ) -> ModelResult:
        from litellm import acompletion

        response = await acompletion(
            model=model,
            api_key=self._api_key_for_model(model),
            messages=[
                {"role": "system", "content": "Return concise, evidence-based JSON-safe text."},
                {"role": "user", "content": prompt[:24000]},
            ],
            response_format={"type": "json_object"},
            max_tokens=self._max_output_tokens(task),
            **self._reasoning_options(model),
            **self._observability_options(task),
        )
        content = response.choices[0].message.content or ""
        cost = float(getattr(response, "_hidden_params", {}).get("response_cost", 0) or 0)
        usage = getattr(response, "usage", None)
        log_event(
            "model_provider_call_succeeded",
            task=task,
            model=model,
            provider=self._provider_for_model(model),
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            estimated_cost_usd=cost,
        )
        return ModelResult(
            content=content,
            model=model,
            provider=self._provider_for_model(model),
            latency_ms=(time.perf_counter() - start) * 1000,
            estimated_cost_usd=cost,
            fallback=False,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )

    def _select_model(self, task: str) -> str:
        candidates = self._candidate_models(task)
        if not candidates:
            raise RuntimeError("No configured model")
        return candidates[0]

    def _candidate_models(self, task: str) -> list[str]:
        candidates: list[str] = []
        if settings.cheap_model and self._is_configured_model(settings.cheap_model):
            candidates.append(settings.cheap_model)
        if settings.openai_api_key:
            candidates.append("gpt-5.6-luna")
        if settings.groq_api_key and task in {"extract", "normalize"}:
            candidates.append("groq/openai/gpt-oss-20b")
        if (
            task not in {"extract", "normalize"}
            and settings.strong_model
            and self._is_configured_model(settings.strong_model)
        ):
            candidates.append(settings.strong_model)
        return list(dict.fromkeys(candidates))[:2]

    def _api_key_for_model(self, model: str) -> str | None:
        if self._is_openai_model(model):
            return settings.openai_api_key
        if model.startswith("groq/"):
            return settings.groq_api_key
        return None

    def _has_configured_model(self, task: str) -> bool:
        return bool(self._candidate_models(task))

    def _is_configured_model(self, model: str) -> bool:
        if self._is_openai_model(model):
            return bool(settings.openai_api_key)
        if model.startswith("groq/"):
            return bool(settings.groq_api_key)
        return False

    @staticmethod
    def _is_openai_model(model: str) -> bool:
        return model.startswith(("gpt-", "o")) or model.startswith("openai/")

    def _provider_for_model(self, model: str) -> str:
        if self._is_openai_model(model):
            return "openai"
        return model.split("/", 1)[0]

    def _observability_options(self, task: str) -> dict[str, Any]:
        if not settings.helicone_api_key:
            return {}
        os.environ["HELICONE_API_KEY"] = settings.helicone_api_key
        return {
            "success_callback": ["helicone"],
            "failure_callback": ["helicone"],
            "metadata": {"app": "resonant", "task": task},
        }

    @staticmethod
    def _max_output_tokens(task: str) -> int:
        return {
            "extract": 900,
            "normalize": 4000,
            "match": 6000,
            "rank": 1500,
        }.get(task, 1800)

    @staticmethod
    def _reasoning_options(model: str) -> dict[str, str]:
        return {}

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code in {408, 409, 429} or (isinstance(status_code, int) and status_code >= 500):
            return True
        name = type(exc).__name__.lower()
        return any(
            marker in name for marker in ("timeout", "rate", "connection", "serviceunavailable")
        )


model_router = ModelRouter()
