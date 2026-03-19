"""Reputation system models — on-chain reputation bridged to platform DB."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReputationTier(str, Enum):
    """Contributor tiers derived from on-chain reputation score."""
    NOVICE = "novice"      # 0-9
    BUILDER = "builder"    # 10-49
    EXPERT = "expert"      # 50-199
    LEGEND = "legend"      # 200+

    @classmethod
    def from_score(cls, score: int) -> "ReputationTier":
        if score >= 200:
            return cls.LEGEND
        if score >= 50:
            return cls.EXPERT
        if score >= 10:
            return cls.BUILDER
        return cls.NOVICE


class BountyTier(int, Enum):
    T1 = 1
    T2 = 2
    T3 = 3


class ReputationChangeReason(str, Enum):
    PR_MERGED = "pr_merged"
    PR_REJECTED = "pr_rejected"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    SYNC = "sync"


# ---------------------------------------------------------------------------
# Core domain objects (Pydantic)
# ---------------------------------------------------------------------------

class ReputationScore(BaseModel):
    """Snapshot of a contributor's on-chain reputation."""
    wallet: str = Field(..., description="Solana wallet address (base-58)")
    score: int = Field(0, ge=0)
    tier: ReputationTier = ReputationTier.NOVICE
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def recalculate_tier(self) -> None:
        self.tier = ReputationTier.from_score(self.score)


class ReputationHistory(BaseModel):
    """A single reputation change event."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wallet: str
    delta: int = Field(..., description="Positive = gain, negative = loss")
    reason: ReputationChangeReason
    bounty_tier: Optional[BountyTier] = None
    tx_signature: Optional[str] = Field(None, description="Solana tx sig")
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CooldownRecord(BaseModel):
    """Tracks cooldown periods after reputation penalties."""
    wallet: str
    bounty_tier: BountyTier
    reason: str = "pr_rejected"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    active: bool = True


class EligibilityCheck(BaseModel):
    """Result of checking whether a wallet can claim a bounty tier."""
    wallet: str
    bounty_tier: BountyTier
    eligible: bool
    reputation_score: int = 0
    reputation_tier: ReputationTier = ReputationTier.NOVICE
    meets_reputation: bool = True
    meets_token_gate: bool = True
    cooldown_active: bool = False
    cooldown_expires_at: Optional[datetime] = None
    reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API response / request schemas
# ---------------------------------------------------------------------------

class ReputationResponse(BaseModel):
    wallet: str
    score: int
    tier: ReputationTier
    last_updated: datetime


class ReputationHistoryResponse(BaseModel):
    items: list[ReputationHistory]
    total: int


class LeaderboardEntry(BaseModel):
    rank: int
    wallet: str
    score: int
    tier: ReputationTier


class ReputationLeaderboardResponse(BaseModel):
    items: list[LeaderboardEntry]
    total: int


class EligibilityResponse(BaseModel):
    wallet: str
    bounty_tier: BountyTier
    eligible: bool
    reputation_score: int
    reputation_tier: ReputationTier
    meets_reputation: bool
    meets_token_gate: bool
    cooldown_active: bool
    cooldown_expires_at: Optional[datetime] = None
    reasons: list[str]


class SyncRequest(BaseModel):
    wallets: Optional[list[str]] = Field(
        None, description="Wallets to sync. None = sync all known wallets.",
    )


class SyncResponse(BaseModel):
    synced: int
    errors: list[str]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Reputation points awarded per bounty tier on PR merge
TIER_REPUTATION_REWARDS: dict[BountyTier, int] = {
    BountyTier.T1: 1,
    BountyTier.T2: 5,
    BountyTier.T3: 20,
}

# Cooldown durations (hours) after repeated rejection
TIER_COOLDOWN_HOURS: dict[BountyTier, int] = {
    BountyTier.T1: 24,       # 24 h
    BountyTier.T2: 168,      # 7 days
    BountyTier.T3: 720,      # 30 days
}

# Minimum $FNDRY token balance to claim T2+ bounties (sybil resistance)
MIN_FNDRY_FOR_TIER: dict[BountyTier, float] = {
    BountyTier.T1: 0.0,
    BountyTier.T2: 100.0,
    BountyTier.T3: 500.0,
}

# Minimum reputation score to claim each tier
MIN_REPUTATION_FOR_TIER: dict[BountyTier, int] = {
    BountyTier.T1: 0,
    BountyTier.T2: 10,
    BountyTier.T3: 50,
}

# Number of consecutive rejections before cooldown kicks in
REJECTION_THRESHOLD = 3
