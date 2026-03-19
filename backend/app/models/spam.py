"""Spam detection Pydantic models."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class SpamCheckRequest(BaseModel):
    """Request body for POST /api/spam/check."""
    pr_number: int = Field(..., description="Pull request number")
    pr_author: str = Field(..., description="GitHub username of PR author")
    pr_title: str = Field("", description="PR title")
    pr_body: str = Field("", description="PR body/description")
    diff: str = Field("", description="PR diff content")
    tier: str = Field("unknown", description="Bounty tier (tier-1, tier-2, tier-3)")
    repo: str = Field("SolFoundry/solfoundry", description="Repository slug")


class SpamCheckDetail(BaseModel):
    """Individual spam check result."""
    check_name: str
    passed: bool
    penalty: float = 0.0
    reason: str = ""


class SpamCheckResponse(BaseModel):
    """Response from spam check."""
    pr_number: int
    pr_author: str
    is_spam: bool
    total_penalty: float
    threshold: float
    details: list[SpamCheckDetail]
    auto_action: str = Field("none", description="Action taken: none, flag, auto-reject")
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SpamHistoryItem(BaseModel):
    """Single item in spam check history."""
    pr_number: int
    pr_author: str
    is_spam: bool
    total_penalty: float
    auto_action: str
    checked_at: datetime


class SpamHistoryResponse(BaseModel):
    """Response for GET /api/spam/history."""
    items: list[SpamHistoryItem]
    total: int
    skip: int
    limit: int


class SpamStatsResponse(BaseModel):
    """Response for GET /api/spam/stats."""
    total_checks: int = 0
    total_flagged: int = 0
    total_auto_rejected: int = 0
    total_clean: int = 0
    false_positives_reported: int = 0
    top_reasons: list[dict] = Field(default_factory=list)
    checks_last_24h: int = 0
    checks_last_7d: int = 0


class SpamConfigUpdate(BaseModel):
    """Request body for PATCH /api/spam/config."""
    velocity_max_prs_per_hour: Optional[int] = Field(None, ge=1, le=50)
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    new_account_days: Optional[int] = Field(None, ge=1, le=90)
    bounty_snipe_max_simultaneous: Optional[int] = Field(None, ge=1, le=50)
    copy_paste_min_block_size: Optional[int] = Field(None, ge=10, le=500)
    ai_slop_boilerplate_threshold: Optional[int] = Field(None, ge=5, le=200)
    penalty_threshold_flag: Optional[float] = Field(None, ge=0.0, le=100.0)
    penalty_threshold_reject: Optional[float] = Field(None, ge=0.0, le=100.0)
    tier_multipliers: Optional[dict[str, float]] = None


class SpamConfigResponse(BaseModel):
    """Current spam detection configuration."""
    velocity_max_prs_per_hour: int
    similarity_threshold: float
    new_account_days: int
    bounty_snipe_max_simultaneous: int
    copy_paste_min_block_size: int
    ai_slop_boilerplate_threshold: int
    penalty_threshold_flag: float
    penalty_threshold_reject: float
    tier_multipliers: dict[str, float]
