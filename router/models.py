"""Pydantic models for the LLM Router."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from router.config import ModelId, TaskType


class ReviewRequest(BaseModel):
    """Incoming review request to be routed to an LLM."""

    task_type: TaskType = TaskType.code_review
    content: str = Field(..., min_length=1, description="Content to review (code diff, doc, etc.)")
    context: Optional[str] = Field(None, description="Additional context (bounty desc, PR body)")
    preferred_model: Optional[ModelId] = Field(
        None, description="Force a specific model (skips routing)"
    )
    max_tokens: Optional[int] = Field(None, ge=64, le=16384)


class ReviewResponse(BaseModel):
    """Result from the LLM review."""

    request_id: str
    model_used: ModelId
    task_type: TaskType
    review_text: str
    tokens_used: int
    cost_usd: float
    latency_ms: float
    fallback_used: bool = Field(
        default=False, description="True if primary model failed and a fallback was used"
    )
    fallback_chain_tried: list[ModelId] = Field(
        default_factory=list,
        description="Models attempted before success",
    )
    created_at: datetime


class CostSummary(BaseModel):
    """Aggregated cost tracking."""

    model_id: ModelId
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class RouterHealthResponse(BaseModel):
    """Health of the LLM router and each provider."""

    healthy: bool
    models: dict[str, bool]  # model_id -> reachable
