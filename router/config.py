"""LLM Router configuration — model definitions and fallback chains."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ModelId(str, Enum):
    GPT_5_4 = "gpt-5.4"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GROK_4 = "grok-4"
    CLAUDE_OPUS_4_6 = "claude-opus-4.6"


class ModelConfig(BaseModel):
    """Configuration for a single LLM provider."""

    model_id: ModelId
    display_name: str
    provider: str
    cost_per_1k_tokens: float = Field(
        ..., description="Cost in USD per 1k tokens"
    )
    max_tokens: int = 4096
    rate_limit_rpm: int = Field(
        default=60, description="Requests per minute"
    )
    timeout_seconds: int = 30
    enabled: bool = True
    api_key_env: str = Field(
        ..., description="Environment variable name for API key"
    )


class TaskType(str, Enum):
    code_review = "code-review"
    security_audit = "security-audit"
    bug_fix = "bug-fix"
    documentation = "documentation"
    general = "general"


# ---------------------------------------------------------------------------
# Default model configs — loaded at import time, overridable via env.
# ---------------------------------------------------------------------------

DEFAULT_MODELS: dict[ModelId, ModelConfig] = {
    ModelId.GPT_5_4: ModelConfig(
        model_id=ModelId.GPT_5_4,
        display_name="GPT-5.4",
        provider="openai",
        cost_per_1k_tokens=0.03,
        max_tokens=8192,
        rate_limit_rpm=60,
        timeout_seconds=30,
        api_key_env="OPENAI_API_KEY",
    ),
    ModelId.GEMINI_2_5_PRO: ModelConfig(
        model_id=ModelId.GEMINI_2_5_PRO,
        display_name="Gemini 2.5 Pro",
        provider="google",
        cost_per_1k_tokens=0.025,
        max_tokens=8192,
        rate_limit_rpm=60,
        timeout_seconds=30,
        api_key_env="GOOGLE_AI_API_KEY",
    ),
    ModelId.GROK_4: ModelConfig(
        model_id=ModelId.GROK_4,
        display_name="Grok 4",
        provider="xai",
        cost_per_1k_tokens=0.02,
        max_tokens=8192,
        rate_limit_rpm=30,
        timeout_seconds=30,
        api_key_env="XAI_API_KEY",
    ),
    ModelId.CLAUDE_OPUS_4_6: ModelConfig(
        model_id=ModelId.CLAUDE_OPUS_4_6,
        display_name="Claude Opus 4.6",
        provider="anthropic",
        cost_per_1k_tokens=0.075,
        max_tokens=8192,
        rate_limit_rpm=40,
        timeout_seconds=45,
        api_key_env="ANTHROPIC_API_KEY",
    ),
}

# Mapping: task-type -> ordered list of preferred models (first = primary).
TASK_ROUTING: dict[TaskType, list[ModelId]] = {
    TaskType.code_review: [
        ModelId.CLAUDE_OPUS_4_6,
        ModelId.GPT_5_4,
        ModelId.GEMINI_2_5_PRO,
        ModelId.GROK_4,
    ],
    TaskType.security_audit: [
        ModelId.CLAUDE_OPUS_4_6,
        ModelId.GPT_5_4,
        ModelId.GROK_4,
        ModelId.GEMINI_2_5_PRO,
    ],
    TaskType.bug_fix: [
        ModelId.GPT_5_4,
        ModelId.CLAUDE_OPUS_4_6,
        ModelId.GEMINI_2_5_PRO,
        ModelId.GROK_4,
    ],
    TaskType.documentation: [
        ModelId.GEMINI_2_5_PRO,
        ModelId.GPT_5_4,
        ModelId.CLAUDE_OPUS_4_6,
        ModelId.GROK_4,
    ],
    TaskType.general: [
        ModelId.GPT_5_4,
        ModelId.GEMINI_2_5_PRO,
        ModelId.GROK_4,
        ModelId.CLAUDE_OPUS_4_6,
    ],
}


def get_fallback_chain(task_type: TaskType) -> list[ModelConfig]:
    """Return ordered list of ModelConfig for given task type."""
    model_ids = TASK_ROUTING.get(task_type, TASK_ROUTING[TaskType.general])
    return [DEFAULT_MODELS[mid] for mid in model_ids if DEFAULT_MODELS[mid].enabled]
