"""AI review and bounty completion flow models.

Pydantic models for submit->review->approve->pay pipeline.
Scored by AI models (GPT/Gemini/Grok) across six categories.

PostgreSQL migration: reviews(id UUID PK, bounty_id UUID, scores JSONB,
overall_score FLOAT, status VARCHAR(20), created_at TIMESTAMPTZ);
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class ReviewStatus(str, Enum):
    """Review lifecycle status."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    SCORED = "scored"
    APPROVED = "approved"
    DISPUTED = "disputed"
    PAID = "paid"

REVIEW_TIER_THRESHOLDS: dict[int, float] = {1: 6.0, 2: 7.0, 3: 8.0}
AUTO_APPROVE_HOURS: int = 48

class ModelScore(BaseModel):
    """Per-model AI reviewer score breakdown."""
    model_name: str = Field(..., min_length=1, max_length=50)
    quality: float = Field(..., ge=0.0, le=10.0)
    correctness: float = Field(..., ge=0.0, le=10.0)
    security: float = Field(..., ge=0.0, le=10.0)
    completeness: float = Field(..., ge=0.0, le=10.0)
    tests: float = Field(..., ge=0.0, le=10.0)
    integration: float = Field(..., ge=0.0, le=10.0)
    model_average: float = Field(0.0, ge=0.0, le=10.0)
    feedback: Optional[str] = Field(None, max_length=5000)

    def compute_average(self) -> float:
        """Arithmetic mean of all six category scores."""
        vals = [self.quality, self.correctness, self.security,
                self.completeness, self.tests, self.integration]
        return round(sum(vals) / len(vals), 2)

class ReviewScoresCreate(BaseModel):
    """Payload for recording AI review scores."""
    scores: list[ModelScore] = Field(..., min_length=1, max_length=5)

    @field_validator("scores")
    @classmethod
    def no_duplicate_models(cls, v: list[ModelScore]) -> list[ModelScore]:
        """Reject duplicate model names."""
        names = [s.model_name.lower() for s in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate model names")
        return v

class ReviewSubmitCreate(BaseModel):
    """Payload for submitting a PR for review."""
    pr_url: str = Field(..., min_length=10, max_length=500)
    contributor_wallet: str = Field(..., min_length=32, max_length=64)
    submitted_by: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("pr_url")
    @classmethod
    def validate_pr_url(cls, v: str) -> str:
        """Validate GitHub pull request URL."""
        if not v.startswith(("https://github.com/", "http://github.com/")):
            raise ValueError("Must be a GitHub URL")
        if "/pull/" not in v:
            raise ValueError("Must contain /pull/")
        return v

class ReviewApproveRequest(BaseModel):
    """Creator approval payload."""
    approved_by: str = Field(..., min_length=1, max_length=100)

class ReviewDisputeRequest(BaseModel):
    """Creator dispute payload."""
    disputed_by: str = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=10, max_length=2000)

class ReviewRecord(BaseModel):
    """In-memory storage model for a review lifecycle."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bounty_id: str
    submission_id: str
    pr_url: str
    contributor_wallet: str
    submitted_by: str
    notes: Optional[str] = None
    status: ReviewStatus = ReviewStatus.PENDING
    scores: list[ModelScore] = Field(default_factory=list)
    overall_score: Optional[float] = None
    meets_threshold: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    disputed_by: Optional[str] = None
    dispute_reason: Optional[str] = None
    disputed_at: Optional[datetime] = None
    payout_tx_hash: Optional[str] = None
    payout_amount: Optional[float] = None
    winner_wallet: Optional[str] = None
    scored_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lifecycle_log: list[dict] = Field(default_factory=list)

class ReviewResponse(ReviewRecord):
    """Full review API response (same fields as ReviewRecord)."""
    model_config = {"from_attributes": True}

class ReviewListItem(BaseModel):
    """Brief review info for list views."""
    id: str
    bounty_id: str
    pr_url: str
    submitted_by: str
    status: ReviewStatus
    overall_score: Optional[float] = None
    meets_threshold: Optional[bool] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class AutoApproveResult(BaseModel):
    """Result of auto-approve check."""
    approved_count: int = 0
    checked_count: int = 0
    details: list[dict] = Field(default_factory=list)
