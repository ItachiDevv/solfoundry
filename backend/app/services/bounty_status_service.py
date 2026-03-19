"""Bounty status transitions triggered by webhook events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.bounty import BountyCreate, BountyDB, BountyStatus, BountyTier
from app.services.bounty_service import _bounty_store, create_bounty

logger = logging.getLogger(__name__)


def find_bounty_by_issue_number(issue_number: int, repo_full_name: str) -> Optional[BountyDB]:
    """Find a bounty whose github_issue_url contains the given issue number and repo."""
    for bounty in _bounty_store.values():
        if bounty.github_issue_url and f"{repo_full_name}/issues/{issue_number}" in bounty.github_issue_url:
            return bounty
    return None


def transition_to_in_progress(bounty: BountyDB) -> bool:
    """Move bounty to in_progress when a PR referencing it is opened."""
    if bounty.status not in (BountyStatus.OPEN, BountyStatus.IN_PROGRESS):
        logger.warning("Cannot transition bounty %s from %s to in_progress", bounty.id, bounty.status)
        return False
    bounty.status = BountyStatus.IN_PROGRESS
    bounty.updated_at = datetime.now(timezone.utc)
    logger.info("Bounty %s transitioned to in_progress", bounty.id)
    return True


def transition_to_completed(bounty: BountyDB) -> bool:
    """Move bounty to completed when the referencing PR is merged."""
    if bounty.status != BountyStatus.IN_PROGRESS:
        logger.warning("Cannot transition bounty %s from %s to completed", bounty.id, bounty.status)
        return False
    bounty.status = BountyStatus.COMPLETED
    bounty.updated_at = datetime.now(timezone.utc)
    logger.info("Bounty %s transitioned to completed", bounty.id)
    return True


def auto_create_bounty_from_issue(issue: dict, repo_full_name: str) -> Optional[str]:
    """Create a bounty record when an issue is labeled 'bounty'."""
    issue_number = issue.get("number")
    issue_url = f"https://github.com/{repo_full_name}/issues/{issue_number}"
    existing = find_bounty_by_issue_number(issue_number, repo_full_name)
    if existing:
        logger.info("Bounty already exists for issue #%s (bounty_id=%s)", issue_number, existing.id)
        return None
    title = issue.get("title", f"Issue #{issue_number}")
    body = issue.get("body") or ""
    resp = create_bounty(BountyCreate(
        title=title,
        description=body[:5000],
        tier=BountyTier.T1,
        reward_amount=100.0,
        github_issue_url=issue_url,
    ))
    logger.info("Auto-created bounty %s for issue #%s", resp.id, issue_number)
    return resp.id
