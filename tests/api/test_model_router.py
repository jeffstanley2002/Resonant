from __future__ import annotations

import asyncio

from app.services.model_router import model_router


def test_model_router_exposes_zero_cost_failure_without_fallback_text() -> None:
    result = asyncio.run(model_router.complete("rank", "Rank this job."))

    assert result.fallback is True
    assert result.estimated_cost_usd == 0
    assert result.content == ""
    assert result.model == "unavailable"
    assert result.provider == "none"


def test_model_router_uses_helicone_callback_without_forwarding_credentials(monkeypatch) -> None:
    monkeypatch.setattr("app.services.model_router.settings.helicone_api_key", "helicone-key")

    options = model_router._observability_options("rank")

    assert options == {
        "success_callback": ["helicone"],
        "failure_callback": ["helicone"],
        "metadata": {"app": "resonant", "task": "rank"},
    }


def test_model_router_retries_transient_error_then_uses_secondary_model(monkeypatch) -> None:
    calls: list[str] = []

    async def fail_models(task, prompt, model, start):
        calls.append(model)
        if model == "gpt-5":
            raise TimeoutError("temporary")
        return model_router_fallback_result(model)

    monkeypatch.setattr("app.services.model_router.settings.cheap_model", "gpt-5")
    monkeypatch.setattr("app.services.model_router.settings.openai_api_key", "openai-key")
    monkeypatch.setattr(model_router, "_litellm_complete", fail_models)

    result = asyncio.run(model_router.complete("extract", "skills"))

    assert calls == ["gpt-5", "gpt-5", "gpt-5.6-luna"]
    assert result.model == "gpt-5.6-luna"
    assert result.attempts == 3


def model_router_fallback_result(model: str):
    from app.services.model_router import ModelResult

    return ModelResult(
        content="{}",
        model=model,
        provider=model.split("/", 1)[0],
        latency_ms=1,
        estimated_cost_usd=0,
        fallback=False,
    )


def test_model_router_uses_cheapest_openai_default_for_all_tasks(monkeypatch) -> None:
    monkeypatch.setattr("app.services.model_router.settings.cheap_model", "")
    monkeypatch.setattr("app.services.model_router.settings.strong_model", "")
    monkeypatch.setattr("app.services.model_router.settings.groq_api_key", "")
    monkeypatch.setattr("app.services.model_router.settings.openai_api_key", "openai-key")

    model = model_router._select_model("match")

    assert model == "gpt-5.6-luna"
    assert model_router._api_key_for_model(model) == "openai-key"


def test_model_router_prefers_explicit_cheap_model_over_default(monkeypatch) -> None:
    monkeypatch.setattr("app.services.model_router.settings.cheap_model", "gpt-5")
    monkeypatch.setattr("app.services.model_router.settings.strong_model", "gpt-5")
    monkeypatch.setattr("app.services.model_router.settings.groq_api_key", "")
    monkeypatch.setattr("app.services.model_router.settings.openai_api_key", "openai-key")

    assert model_router._select_model("match") == "gpt-5"


def test_model_router_keeps_strong_model_as_secondary_fallback(monkeypatch) -> None:
    monkeypatch.setattr("app.services.model_router.settings.cheap_model", "gpt-5.6-luna")
    monkeypatch.setattr("app.services.model_router.settings.strong_model", "gpt-5.6-terra")
    monkeypatch.setattr("app.services.model_router.settings.groq_api_key", "")
    monkeypatch.setattr("app.services.model_router.settings.openai_api_key", "openai-key")

    assert model_router._candidate_models("match") == ["gpt-5.6-luna", "gpt-5.6-terra"]


def test_model_router_bounds_output_by_task() -> None:
    assert model_router._max_output_tokens("extract") == 900
    assert model_router._max_output_tokens("normalize") == 4000
    assert model_router._max_output_tokens("match") == 6000
    assert model_router._max_output_tokens("rank") == 1500


def test_model_router_keeps_provider_specific_reasoning_options_empty() -> None:
    assert model_router._reasoning_options("gpt-5.6-luna") == {}
    assert model_router._reasoning_options("groq/openai/gpt-oss-20b") == {}


def test_model_router_does_not_repeat_a_call_that_exhausted_its_own_deadline(monkeypatch) -> None:
    """A wait_for deadline means the call already burned the full timeout.

    Re-running it identically only burns the budget the fallback model needs.
    """
    calls: list[str] = []

    async def hang(task, prompt, model, start):
        calls.append(model)
        await asyncio.sleep(5)
        raise AssertionError("should have been cancelled")

    monkeypatch.setattr("app.services.model_router.settings.cheap_model", "gpt-5")
    monkeypatch.setattr("app.services.model_router.settings.strong_model", "gpt-5.6-terra")
    monkeypatch.setattr("app.services.model_router.settings.openai_api_key", "openai-key")
    monkeypatch.setattr("app.services.model_router.settings.model_call_timeout_seconds", 0.05)
    monkeypatch.setattr("app.services.model_router.settings.model_task_budget_seconds", 5.0)
    monkeypatch.setattr(model_router, "_litellm_complete", hang)

    result = asyncio.run(model_router.complete("match", "match these"))

    # One attempt per candidate model, with no identical retry of the timed-out call.
    assert calls == ["gpt-5", "gpt-5.6-luna"]
    assert result.fallback is True
    assert result.fallback_reason == "provider_error"


def test_model_router_skips_attempts_the_budget_cannot_complete(monkeypatch) -> None:
    calls: list[str] = []

    async def hang(task, prompt, model, start):
        calls.append(model)
        await asyncio.sleep(5)
        raise AssertionError("should have been cancelled")

    monkeypatch.setattr("app.services.model_router.settings.cheap_model", "gpt-5")
    monkeypatch.setattr("app.services.model_router.settings.strong_model", "gpt-5.6-terra")
    monkeypatch.setattr("app.services.model_router.settings.openai_api_key", "openai-key")
    monkeypatch.setattr("app.services.model_router.settings.model_call_timeout_seconds", 0.2)
    # Budget covers one full call timeout only; the second must not start on a slice
    # of time too short to ever succeed.
    monkeypatch.setattr("app.services.model_router.settings.model_task_budget_seconds", 0.3)
    monkeypatch.setattr(model_router, "_litellm_complete", hang)

    result = asyncio.run(model_router.complete("match", "match these"))

    assert calls == ["gpt-5"]
    assert result.attempts == 1
