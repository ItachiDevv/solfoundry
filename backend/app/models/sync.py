"""Models for GitHub <-> Platform bi-directional sync."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SyncDirection(str, Enum):
    """Direction of the sync operation."""
    GITHUB_TO_PLATFORM = "github_to_platform"
    PLATFORM_TO_GITHUB = "platform_to_github"


class SyncStatus(str, Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    RETRYING = "retrying"


class BountyStatus(str, Enum):
    """Status of a bounty."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BountyTier(str, Enum):
    """Bounty difficulty / reward tier."""
    TIER_1 = "tier-1"
    TIER_2 = "tier-2"
    TIER_3 = "tier-3"


class ConflictResolution(str, Enum):
    """Strategy for resolving sync conflicts."""
    GITHUB_WINS = "github_wins"  # GitHub is source of truth (default)
    PLATFORM_WINS = "platform_wins"
    MANUAL = "manual"


# ── Label mappings ────────────────────────────────────────────────────

TIER_LABELS: dict[str, BountyTier] = {
    "tier-1": BountyTier.TIER_1,
    "tier-2": BountyTier.TIER_2,
    "tier-3": BountyTier.TIER_3,
}

CATEGORY_LABELS: set[str] = {
    "frontend", "backend", "smart-contract", "design",
    "documentation", "testing", "devops", "security",
}

STATUS_LABELS: dict[str, BountyStatus] = {
    "in-progress": BountyStatus.IN_PROGRESS,
    "completed": BountyStatus.COMPLETED,
    "cancelled": BountyStatus.CANCELLED,
}


# ── Bounty record ────────────────────────────────────────────────────

class BountyRecord(BaseModel):
    """A bounty record synced between GitHub and the platform."""
    id: str
    github_issue_number: int
    github_repo: str  # e.g. "SolFoundry/solfoundry"
    title: str
    description: str = ""
    status: BountyStatus = BountyStatus.OPEN
    tier: Optional[BountyTier] = None
    categories: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    creator: str = ""
    assignee: Optional[str] = None
    reward_amount: Optional[float] = None
    github_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_synced_at: Optional[datetime] = None


# ── Sync record ──────────────────────────────────────────────────────

class SyncRecord(BaseModel):
    """An individual sync operation record."""
    id: str
    direction: SyncDirection
    entity_type: str = "bounty"
    entity_id: str  # bounty id or github issue number
    status: SyncStatus = SyncStatus.PENDING
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    conflict_resolution: ConflictResolution = ConflictResolution.GITHUB_WINS


# ── API response models ──────────────────────────────────────────────

class SyncStatusDashboard(BaseModel):
    """Dashboard showing overall sync health."""
    last_sync_time: Optional[datetime] = None
    total_syncs: int = 0
    pending_syncs: int = 0
    failed_syncs: int = 0
    completed_syncs: int = 0
    conflict_count: int = 0
    recent_errors: list[dict[str, Any]] = Field(default_factory=list)
    bounty_count: int = 0


class SyncRecordResponse(BaseModel):
    """API response for a sync record."""
    id: str
    direction: SyncDirection
    entity_type: str
    entity_id: str
    status: SyncStatus
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None


class BountyCreateRequest(BaseModel):
    """Request to create a bounty from the platform (triggers GitHub issue creation)."""
    title: str
    description: str = ""
    tier: Optional[BountyTier] = None
    categories: list[str] = Field(default_factory=list)
    reward_amount: Optional[float] = None
    repo: str = "SolFoundry/solfoundry"


class BountyResponse(BaseModel):
    """API response for a bounty."""
    id: str
    github_issue_number: int
    github_repo: str
    title: str
    description: str
    status: BountyStatus
    tier: Optional[BountyTier] = None
    categories: list[str]
    labels: list[str]
    creator: str
    assignee: Optional[str] = None
    reward_amount: Optional[float] = None
    github_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_synced_at: Optional[datetime] = None
