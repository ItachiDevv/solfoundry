"""Bounty data models for the in-memory MVP store."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BountyTier(int, Enum):
    """Bounty difficulty tier."""
    T1 = 1
    T2 = 2
    T3 = 3


class BountyStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAID = "paid"


class BountyDB(BaseModel):
    """In-memory bounty record consumed by the search engine."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    tier: BountyTier = BountyTier.T2
    reward_amount: float
    status: BountyStatus = BountyStatus.OPEN
    github_issue_url: Optional[str] = None
    required_skills: list[str] = []
    deadline: Optional[datetime] = None
    created_by: str = "system"
    claim_count: int = 0
    submission_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
