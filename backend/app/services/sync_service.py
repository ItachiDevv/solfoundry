"""Bi-directional sync service between GitHub issues and platform bounties.

Design decisions:
- GitHub is the source of truth when conflicts arise.
- In-memory stores (consistent with the MVP pattern used elsewhere).
- Retry queue held in memory with configurable max retries.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.sync import (
    BountyCreateRequest,
    BountyRecord,
    BountyResponse,
    BountyStatus,
    BountyTier,
    CATEGORY_LABELS,
    ConflictResolution,
    STATUS_LABELS,
    SyncDirection,
    SyncRecord,
    SyncRecordResponse,
    SyncStatus,
    SyncStatusDashboard,
    TIER_LABELS,
)
from app.services.github_client import GitHubClient, GitHubClientError, get_client

logger = logging.getLogger(__name__)

# ── In-memory stores ─────────────────────────────────────────────────

_bounties: dict[str, BountyRecord] = {}
_sync_records: dict[str, SyncRecord] = {}
_retry_queue: list[str] = []  # sync-record ids awaiting retry
_last_sync_time: Optional[datetime] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _extract_tier(labels: list[str]) -> Optional[BountyTier]:
    """Extract bounty tier from a list of label names."""
    for lbl in labels:
        name = lbl if isinstance(lbl, str) else lbl.get("name", "") if isinstance(lbl, dict) else ""
        if name in TIER_LABELS:
            return TIER_LABELS[name]
    return None


def _extract_categories(labels: list[str | dict[str, Any]]) -> list[str]:
    """Extract category labels from a list of label names/objects."""
    cats: list[str] = []
    for lbl in labels:
        name = lbl if isinstance(lbl, str) else lbl.get("name", "") if isinstance(lbl, dict) else ""
        if name in CATEGORY_LABELS:
            cats.append(name)
    return cats


def _extract_status_from_labels(labels: list[str | dict[str, Any]]) -> Optional[BountyStatus]:
    """Derive bounty status from labels."""
    for lbl in labels:
        name = lbl if isinstance(lbl, str) else lbl.get("name", "") if isinstance(lbl, dict) else ""
        if name in STATUS_LABELS:
            return STATUS_LABELS[name]
    return None


def _label_names(labels: list[Any]) -> list[str]:
    """Normalise a mixed list of label strings / dicts to plain names."""
    result: list[str] = []
    for lbl in labels:
        if isinstance(lbl, str):
            result.append(lbl)
        elif isinstance(lbl, dict) and "name" in lbl:
            result.append(lbl["name"])
    return result


def _find_bounty_by_issue(repo: str, issue_number: int) -> Optional[BountyRecord]:
    """Find a bounty record by its GitHub issue."""
    for b in _bounties.values():
        if b.github_repo == repo and b.github_issue_number == issue_number:
            return b
    return None


def _bounty_to_response(b: BountyRecord) -> BountyResponse:
    return BountyResponse(**b.model_dump())


def _new_sync_record(
    direction: SyncDirection,
    entity_id: str,
    payload: dict[str, Any] | None = None,
) -> SyncRecord:
    rec = SyncRecord(
        id=str(uuid.uuid4()),
        direction=direction,
        entity_id=entity_id,
        payload=payload or {},
    )
    _sync_records[rec.id] = rec
    return rec


def _complete_sync(rec: SyncRecord, *, error: str | None = None) -> None:
    global _last_sync_time
    now = datetime.now(timezone.utc)
    if error:
        rec.status = SyncStatus.FAILED
        rec.error_message = error
        if rec.retry_count < rec.max_retries:
            rec.retry_count += 1
            rec.status = SyncStatus.RETRYING
            _retry_queue.append(rec.id)
    else:
        rec.status = SyncStatus.COMPLETED
        rec.completed_at = now
    _last_sync_time = now


# ── GitHub -> Platform sync ──────────────────────────────────────────

def _is_bounty_issue(issue: dict[str, Any]) -> bool:
    """Check if an issue qualifies as a bounty (has the 'bounty' label)."""
    labels = _label_names(issue.get("labels", []))
    return "bounty" in labels


def sync_issue_opened(issue: dict[str, Any], repo_full_name: str) -> Optional[BountyRecord]:
    """GitHub -> Platform: new bounty issue opened."""
    if not _is_bounty_issue(issue):
        return None

    issue_number = issue["number"]
    existing = _find_bounty_by_issue(repo_full_name, issue_number)
    if existing:
        # Already tracked — update instead
        return sync_issue_labeled(issue, repo_full_name)

    labels = _label_names(issue.get("labels", []))
    bounty_id = str(uuid.uuid4())
    bounty = BountyRecord(
        id=bounty_id,
        github_issue_number=issue_number,
        github_repo=repo_full_name,
        title=issue.get("title", ""),
        description=issue.get("body") or "",
        status=_extract_status_from_labels(labels) or BountyStatus.OPEN,
        tier=_extract_tier(labels),
        categories=_extract_categories(labels),
        labels=labels,
        creator=issue.get("user", {}).get("login", ""),
        assignee=(issue.get("assignee") or {}).get("login") if issue.get("assignee") else None,
        github_url=issue.get("html_url"),
        last_synced_at=datetime.now(timezone.utc),
    )
    _bounties[bounty_id] = bounty

    rec = _new_sync_record(SyncDirection.GITHUB_TO_PLATFORM, bounty_id, {"action": "created"})
    _complete_sync(rec)
    logger.info("Synced new bounty %s from issue #%s", bounty_id, issue_number)
    return bounty


def sync_issue_labeled(issue: dict[str, Any], repo_full_name: str) -> Optional[BountyRecord]:
    """GitHub -> Platform: labels changed on a bounty issue."""
    issue_number = issue["number"]
    bounty = _find_bounty_by_issue(repo_full_name, issue_number)

    # If it just gained the bounty label, create the record
    if bounty is None:
        if _is_bounty_issue(issue):
            return sync_issue_opened(issue, repo_full_name)
        return None

    labels = _label_names(issue.get("labels", []))
    now = datetime.now(timezone.utc)
    bounty.labels = labels
    bounty.tier = _extract_tier(labels)
    bounty.categories = _extract_categories(labels)
    label_status = _extract_status_from_labels(labels)
    if label_status:
        bounty.status = label_status
    bounty.title = issue.get("title", bounty.title)
    bounty.description = issue.get("body") or bounty.description
    bounty.updated_at = now
    bounty.last_synced_at = now

    rec = _new_sync_record(SyncDirection.GITHUB_TO_PLATFORM, bounty.id, {"action": "label_update"})
    _complete_sync(rec)
    logger.info("Updated bounty %s labels from issue #%s", bounty.id, issue_number)
    return bounty


def sync_issue_closed(issue: dict[str, Any], repo_full_name: str) -> Optional[BountyRecord]:
    """GitHub -> Platform: issue closed -> mark bounty completed or cancelled."""
    issue_number = issue["number"]
    bounty = _find_bounty_by_issue(repo_full_name, issue_number)
    if bounty is None:
        return None

    now = datetime.now(timezone.utc)
    labels = _label_names(issue.get("labels", []))

    # If "completed" label present, mark completed; otherwise cancelled
    if "completed" in labels:
        bounty.status = BountyStatus.COMPLETED
    else:
        bounty.status = BountyStatus.CANCELLED
    bounty.updated_at = now
    bounty.last_synced_at = now

    rec = _new_sync_record(SyncDirection.GITHUB_TO_PLATFORM, bounty.id, {"action": "closed"})
    _complete_sync(rec)
    logger.info("Closed bounty %s (status=%s) from issue #%s", bounty.id, bounty.status, issue_number)
    return bounty


# ── Platform -> GitHub sync ──────────────────────────────────────────

async def create_bounty_on_github(
    data: BountyCreateRequest,
    client: GitHubClient | None = None,
) -> BountyRecord:
    """Platform -> GitHub: create a bounty issue on GitHub.

    Creates the issue, then stores the bounty record locally.
    """
    gh = client or get_client()

    labels = ["bounty"]
    if data.tier:
        labels.append(data.tier.value)
    labels.extend(data.categories)

    body = data.description
    if data.reward_amount is not None:
        body += f"\n\n**Reward:** {data.reward_amount} SOL"

    rec = _new_sync_record(SyncDirection.PLATFORM_TO_GITHUB, "pending", {"action": "create_issue"})

    try:
        gh_issue = await gh.create_issue(
            repo=data.repo,
            title=data.title,
            body=body,
            labels=labels,
        )
    except GitHubClientError as exc:
        _complete_sync(rec, error=str(exc))
        raise

    bounty_id = str(uuid.uuid4())
    bounty = BountyRecord(
        id=bounty_id,
        github_issue_number=gh_issue["number"],
        github_repo=data.repo,
        title=data.title,
        description=data.description,
        status=BountyStatus.OPEN,
        tier=data.tier,
        categories=data.categories,
        labels=labels,
        creator="platform",
        reward_amount=data.reward_amount,
        github_url=gh_issue.get("html_url"),
        last_synced_at=datetime.now(timezone.utc),
    )
    _bounties[bounty_id] = bounty

    rec.entity_id = bounty_id
    _complete_sync(rec)
    logger.info("Created GitHub issue #%s for bounty %s", gh_issue["number"], bounty_id)
    return bounty


async def comment_bounty_claimed(
    bounty_id: str,
    claimer: str,
    client: GitHubClient | None = None,
) -> bool:
    """Platform -> GitHub: post a comment when a bounty is claimed."""
    bounty = _bounties.get(bounty_id)
    if not bounty:
        logger.warning("Bounty %s not found for claim comment", bounty_id)
        return False

    gh = client or get_client()
    rec = _new_sync_record(SyncDirection.PLATFORM_TO_GITHUB, bounty_id, {"action": "claim_comment"})

    body = (
        f"This bounty has been claimed by **@{claimer}**.\n\n"
        f"Status has been updated to **in-progress**."
    )

    try:
        await gh.add_comment(bounty.github_repo, bounty.github_issue_number, body)
        await gh.add_labels(bounty.github_repo, bounty.github_issue_number, ["in-progress"])
    except GitHubClientError as exc:
        _complete_sync(rec, error=str(exc))
        return False

    bounty.status = BountyStatus.IN_PROGRESS
    bounty.assignee = claimer
    bounty.updated_at = datetime.now(timezone.utc)
    bounty.last_synced_at = datetime.now(timezone.utc)
    _complete_sync(rec)
    logger.info("Posted claim comment on issue #%s for bounty %s", bounty.github_issue_number, bounty_id)
    return True


# ── Conflict resolution ──────────────────────────────────────────────

def resolve_conflict(
    bounty_id: str,
    github_data: dict[str, Any],
    platform_data: dict[str, Any],
    strategy: ConflictResolution = ConflictResolution.GITHUB_WINS,
) -> BountyRecord | None:
    """Resolve a conflict between GitHub and platform data.

    Default: GitHub wins (source of truth).
    """
    bounty = _bounties.get(bounty_id)
    if not bounty:
        return None

    rec = _new_sync_record(
        SyncDirection.GITHUB_TO_PLATFORM, bounty_id,
        {"action": "conflict_resolution", "strategy": strategy.value},
    )

    if strategy == ConflictResolution.GITHUB_WINS:
        # Apply GitHub data
        labels = _label_names(github_data.get("labels", []))
        bounty.title = github_data.get("title", bounty.title)
        bounty.description = github_data.get("body") or bounty.description
        bounty.labels = labels
        bounty.tier = _extract_tier(labels)
        bounty.categories = _extract_categories(labels)
        label_status = _extract_status_from_labels(labels)
        if label_status:
            bounty.status = label_status
    elif strategy == ConflictResolution.PLATFORM_WINS:
        # Keep platform data (already in memory), nothing to change
        pass
    else:
        rec.status = SyncStatus.CONFLICT
        _sync_records[rec.id] = rec
        return bounty

    bounty.updated_at = datetime.now(timezone.utc)
    bounty.last_synced_at = datetime.now(timezone.utc)
    _complete_sync(rec)
    return bounty


# ── Retry queue processing ───────────────────────────────────────────

async def process_retry_queue(client: GitHubClient | None = None) -> int:
    """Process pending retries. Returns the number of successfully retried items."""
    processed = 0
    remaining: list[str] = []

    for sync_id in _retry_queue:
        rec = _sync_records.get(sync_id)
        if rec is None:
            continue
        if rec.retry_count >= rec.max_retries:
            rec.status = SyncStatus.FAILED
            rec.error_message = (rec.error_message or "") + " [max retries exceeded]"
            continue

        # For platform->github retries we would re-attempt the API call;
        # for github->platform retries, we re-parse the stored payload.
        if rec.direction == SyncDirection.GITHUB_TO_PLATFORM:
            # Re-apply cached payload
            payload = rec.payload
            action = payload.get("action")
            if action == "created" and "issue" in payload:
                sync_issue_opened(payload["issue"], payload.get("repo", ""))
            _complete_sync(rec)
            processed += 1
        else:
            # Platform -> GitHub retries would need the original request;
            # for MVP we just mark as failed if payload is incomplete.
            remaining.append(sync_id)

    _retry_queue.clear()
    _retry_queue.extend(remaining)
    return processed


# ── Query helpers ────────────────────────────────────────────────────

def get_dashboard() -> SyncStatusDashboard:
    """Build the sync status dashboard."""
    records = list(_sync_records.values())
    pending = sum(1 for r in records if r.status in (SyncStatus.PENDING, SyncStatus.IN_PROGRESS, SyncStatus.RETRYING))
    failed = sum(1 for r in records if r.status == SyncStatus.FAILED)
    completed = sum(1 for r in records if r.status == SyncStatus.COMPLETED)
    conflicts = sum(1 for r in records if r.status == SyncStatus.CONFLICT)

    recent_errors = [
        {"id": r.id, "error": r.error_message, "entity_id": r.entity_id, "created_at": r.created_at.isoformat()}
        for r in sorted(records, key=lambda x: x.created_at, reverse=True)
        if r.status == SyncStatus.FAILED
    ][:10]

    return SyncStatusDashboard(
        last_sync_time=_last_sync_time,
        total_syncs=len(records),
        pending_syncs=pending,
        failed_syncs=failed,
        completed_syncs=completed,
        conflict_count=conflicts,
        recent_errors=recent_errors,
        bounty_count=len(_bounties),
    )


def get_bounty(bounty_id: str) -> Optional[BountyResponse]:
    b = _bounties.get(bounty_id)
    return _bounty_to_response(b) if b else None


def list_bounties(
    status: Optional[BountyStatus] = None,
    tier: Optional[BountyTier] = None,
    skip: int = 0,
    limit: int = 20,
) -> list[BountyResponse]:
    results = list(_bounties.values())
    if status:
        results = [b for b in results if b.status == status]
    if tier:
        results = [b for b in results if b.tier == tier]
    return [_bounty_to_response(b) for b in results[skip : skip + limit]]


def get_sync_records(
    status: Optional[SyncStatus] = None,
    direction: Optional[SyncDirection] = None,
    skip: int = 0,
    limit: int = 20,
) -> list[SyncRecordResponse]:
    records = list(_sync_records.values())
    if status:
        records = [r for r in records if r.status == status]
    if direction:
        records = [r for r in records if r.direction == direction]
    records.sort(key=lambda r: r.created_at, reverse=True)
    return [
        SyncRecordResponse(
            id=r.id, direction=r.direction, entity_type=r.entity_type,
            entity_id=r.entity_id, status=r.status, error_message=r.error_message,
            retry_count=r.retry_count, created_at=r.created_at, completed_at=r.completed_at,
        )
        for r in records[skip : skip + limit]
    ]


# ── Store management (mainly for tests) ──────────────────────────────

def clear_stores() -> None:
    """Reset all in-memory stores. Intended for test isolation."""
    global _last_sync_time
    _bounties.clear()
    _sync_records.clear()
    _retry_queue.clear()
    _last_sync_time = None
