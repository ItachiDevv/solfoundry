"""Tests for the LLM router."""

import pytest

from router.config import ModelId, TaskType, DEFAULT_MODELS, ModelConfig
from router.llm_router import LLMRouter, LLMRouterError
from router.models import ReviewRequest
from router.rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_provider(response_text: str = "LGTM", tokens: int = 150):
    """Return a provider_fn that always succeeds with the given response."""

    def _fn(cfg: ModelConfig, prompt: str, max_tokens: int) -> tuple[str, int]:
        return response_text, tokens

    return _fn


def _failing_provider(fail_models: set[ModelId]):
    """Return a provider_fn that fails for specific models."""

    def _fn(cfg: ModelConfig, prompt: str, max_tokens: int) -> tuple[str, int]:
        if cfg.model_id in fail_models:
            raise RuntimeError(f"Simulated failure for {cfg.model_id.value}")
        return "Fallback review", 200

    return _fn


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


class TestLLMRouterRoute:
    def test_route_success(self):
        router = LLMRouter(provider_fn=_fake_provider("Looks good", 100))
        req = ReviewRequest(
            task_type=TaskType.code_review,
            content="def hello(): pass",
        )
        resp = router.route(req)
        assert resp.review_text == "Looks good"
        assert resp.tokens_used == 100
        assert resp.cost_usd > 0
        assert resp.fallback_used is False

    def test_route_preferred_model(self):
        router = LLMRouter(provider_fn=_fake_provider())
        req = ReviewRequest(
            task_type=TaskType.general,
            content="some code",
            preferred_model=ModelId.GROK_4,
        )
        resp = router.route(req)
        assert resp.model_used == ModelId.GROK_4

    def test_fallback_on_primary_failure(self):
        # Fail Claude (primary for code-review), succeed on GPT-5.4
        router = LLMRouter(
            provider_fn=_failing_provider({ModelId.CLAUDE_OPUS_4_6})
        )
        req = ReviewRequest(
            task_type=TaskType.code_review,
            content="fn main() {}",
        )
        resp = router.route(req)
        assert resp.model_used == ModelId.GPT_5_4
        assert resp.fallback_used is True
        assert ModelId.CLAUDE_OPUS_4_6 in resp.fallback_chain_tried

    def test_all_models_fail_raises(self):
        def _always_fail(cfg, prompt, max_tokens):
            raise RuntimeError("boom")

        router = LLMRouter(provider_fn=_always_fail)
        req = ReviewRequest(task_type=TaskType.general, content="x")
        with pytest.raises(LLMRouterError, match="All models in fallback chain failed"):
            router.route(req)

    def test_cost_tracking(self):
        router = LLMRouter(provider_fn=_fake_provider("ok", 1000))
        req = ReviewRequest(task_type=TaskType.code_review, content="code")
        resp = router.route(req)

        costs = router.get_cost_summary()
        model_cost = router.get_cost_for_model(resp.model_used)
        assert model_cost.total_requests == 1
        assert model_cost.total_tokens == 1000
        assert model_cost.total_cost_usd > 0

    def test_context_included_in_prompt(self):
        """Ensure context is passed through to the provider."""
        captured = {}

        def _capture(cfg, prompt, max_tokens):
            captured["prompt"] = prompt
            return "ok", 50

        router = LLMRouter(provider_fn=_capture)
        req = ReviewRequest(
            task_type=TaskType.code_review,
            content="diff here",
            context="Bounty: fix auth bug",
        )
        router.route(req)
        assert "Bounty: fix auth bug" in captured["prompt"]
        assert "diff here" in captured["prompt"]


# ---------------------------------------------------------------------------
# Rate limiter tests
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter()
        for _ in range(5):
            assert rl.allow("test-model", max_rpm=5) is True

    def test_blocks_over_limit(self):
        rl = RateLimiter()
        for _ in range(3):
            rl.allow("test-model", max_rpm=3)
        assert rl.allow("test-model", max_rpm=3) is False

    def test_separate_models(self):
        rl = RateLimiter()
        for _ in range(3):
            rl.allow("model-a", max_rpm=3)
        # model-b should still be allowed
        assert rl.allow("model-b", max_rpm=3) is True

    def test_reset_single(self):
        rl = RateLimiter()
        for _ in range(3):
            rl.allow("model-a", max_rpm=3)
        rl.reset("model-a")
        assert rl.allow("model-a", max_rpm=3) is True

    def test_reset_all(self):
        rl = RateLimiter()
        for _ in range(3):
            rl.allow("m1", max_rpm=3)
            rl.allow("m2", max_rpm=3)
        rl.reset()
        assert rl.allow("m1", max_rpm=3) is True
        assert rl.allow("m2", max_rpm=3) is True


# ---------------------------------------------------------------------------
# Router API endpoint tests (via FastAPI TestClient)
# ---------------------------------------------------------------------------


class TestRouterAPI:
    @pytest.fixture(autouse=True)
    def setup_router(self):
        """Swap module-level router with a test-friendly one."""
        import router.api as router_api

        original = router_api._llm_router
        router_api._llm_router = LLMRouter(provider_fn=_fake_provider("Test review", 200))
        yield
        router_api._llm_router = original

    @pytest.fixture
    def api_client(self):
        from fastapi.testclient import TestClient
        from app.main import app

        return TestClient(app)

    def test_submit_review(self, api_client):
        resp = api_client.post(
            "/api/router/review",
            json={"task_type": "code-review", "content": "def foo(): pass"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["review_text"] == "Test review"
        assert body["tokens_used"] == 200

    def test_get_costs(self, api_client):
        # Submit one review to populate cost data
        api_client.post(
            "/api/router/review",
            json={"task_type": "general", "content": "x"},
        )
        resp = api_client.get("/api/router/costs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_model_cost(self, api_client):
        resp = api_client.get(f"/api/router/costs/{ModelId.GPT_5_4.value}")
        assert resp.status_code == 200

    def test_router_health(self, api_client):
        resp = api_client.get("/api/router/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["healthy"] is True
        assert "gpt-5.4" in body["models"]
