"""LLM Router — routes review requests to the best model with fallback chain.

The router:
1. Selects the appropriate fallback chain based on task type.
2. Tries each model in order until one succeeds.
3. Enforces per-model rate limits.
4. Tracks cost per review.

In production the ``_call_model`` method would make real HTTP calls to each
provider's API.  For the MVP it uses a pluggable ``_provider_fn`` so tests
can inject a fake.
"""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Optional

from router.config import (
    DEFAULT_MODELS,
    ModelConfig,
    ModelId,
    TaskType,
    get_fallback_chain,
)
from router.models import CostSummary, ReviewRequest, ReviewResponse
from router.rate_limiter import RateLimiter


class LLMRouterError(Exception):
    """Raised when no model in the fallback chain can serve the request."""


# Type alias for the provider call function.
# Signature: (model_config, prompt, max_tokens) -> (response_text, tokens_used)
ProviderFn = Callable[[ModelConfig, str, int], tuple[str, int]]


class LLMRouter:
    """Stateful router that picks the right LLM and falls back on failure."""

    def __init__(
        self,
        models: dict[ModelId, ModelConfig] | None = None,
        provider_fn: ProviderFn | None = None,
    ) -> None:
        self.models = models or dict(DEFAULT_MODELS)
        self._rate_limiter = RateLimiter()
        self._provider_fn: ProviderFn | None = provider_fn

        # Cost tracking
        self._cost_ledger: dict[ModelId, CostSummary] = {
            mid: CostSummary(model_id=mid)
            for mid in self.models
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, request: ReviewRequest) -> ReviewResponse:
        """Route a review request through the fallback chain and return result."""
        # Build prompt
        prompt = self._build_prompt(request)
        max_tokens = request.max_tokens or 4096

        # Determine model chain
        if request.preferred_model:
            chain = [self.models[request.preferred_model]]
        else:
            chain = get_fallback_chain(request.task_type)

        tried: list[ModelId] = []
        last_error: Exception | None = None

        for cfg in chain:
            if not cfg.enabled:
                continue

            # Rate-limit check
            if not self._rate_limiter.allow(cfg.model_id.value, cfg.rate_limit_rpm):
                tried.append(cfg.model_id)
                last_error = LLMRouterError(
                    f"Rate limited: {cfg.model_id.value}"
                )
                continue

            try:
                start = time.monotonic()
                text, tokens = self._call_model(cfg, prompt, max_tokens)
                latency_ms = round((time.monotonic() - start) * 1000, 2)

                cost = round(tokens / 1000 * cfg.cost_per_1k_tokens, 6)
                self._record_cost(cfg.model_id, tokens, cost)

                return ReviewResponse(
                    request_id=str(uuid.uuid4()),
                    model_used=cfg.model_id,
                    task_type=request.task_type,
                    review_text=text,
                    tokens_used=tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    fallback_used=len(tried) > 0,
                    fallback_chain_tried=tried,
                    created_at=datetime.now(timezone.utc),
                )
            except Exception as exc:  # noqa: BLE001
                tried.append(cfg.model_id)
                last_error = exc
                continue

        raise LLMRouterError(
            f"All models in fallback chain failed for task {request.task_type.value}. "
            f"Tried: {[m.value for m in tried]}. Last error: {last_error}"
        )

    def get_cost_summary(self) -> list[CostSummary]:
        """Return cost summary for all models."""
        return list(self._cost_ledger.values())

    def get_cost_for_model(self, model_id: ModelId) -> CostSummary:
        return self._cost_ledger[model_id]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_prompt(self, request: ReviewRequest) -> str:
        parts = [f"Task type: {request.task_type.value}"]
        if request.context:
            parts.append(f"Context:\n{request.context}")
        parts.append(f"Content to review:\n{request.content}")
        return "\n\n".join(parts)

    def _call_model(
        self, cfg: ModelConfig, prompt: str, max_tokens: int
    ) -> tuple[str, int]:
        """Call the LLM provider. Uses injected provider_fn if available."""
        if self._provider_fn is not None:
            return self._provider_fn(cfg, prompt, max_tokens)

        # In production this would dispatch to httpx calls per provider.
        # For now, raise so the fallback chain logic is exercised in tests.
        api_key = os.environ.get(cfg.api_key_env)
        if not api_key:
            raise LLMRouterError(
                f"Missing API key env var {cfg.api_key_env} for {cfg.model_id.value}"
            )

        # Placeholder — real implementation would call the provider SDK.
        raise NotImplementedError(
            f"Real HTTP call to {cfg.provider} not yet implemented"
        )

    def _record_cost(self, model_id: ModelId, tokens: int, cost: float) -> None:
        summary = self._cost_ledger[model_id]
        summary.total_requests += 1
        summary.total_tokens += tokens
        summary.total_cost_usd = round(summary.total_cost_usd + cost, 6)
