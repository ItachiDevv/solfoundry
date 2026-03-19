"""Anti-spam API router."""

import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Header

from app.models.spam import (
    SpamCheckRequest,
    SpamCheckResponse,
    SpamConfigResponse,
    SpamConfigUpdate,
    SpamHistoryResponse,
    SpamStatsResponse,
)
from app.services import spam_detector

router = APIRouter(prefix="/spam", tags=["spam"])

# Simple admin key check — in production use proper auth middleware
ADMIN_API_KEY = "solfoundry-admin"  # Overridden via env var in production


def _verify_admin(authorization: Optional[str]) -> None:
    """Verify the request carries a valid admin bearer token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    match = re.match(r"Bearer\s+(.+)", authorization, re.IGNORECASE)
    if not match or match.group(1) != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")


@router.post("/check", response_model=SpamCheckResponse)
async def check_pr_spam(body: SpamCheckRequest):
    """Run spam detection checks on a PR submission."""
    # Extract bounty issue from PR body if available
    bounty_issue = None
    issue_match = re.search(r"(?:closes|fixes|resolves)\s+#(\d+)", (body.pr_body or "").lower())
    if issue_match:
        bounty_issue = int(issue_match.group(1))

    result = spam_detector.run_spam_check(
        pr_number=body.pr_number,
        pr_author=body.pr_author,
        pr_title=body.pr_title,
        pr_body=body.pr_body,
        diff=body.diff,
        tier=body.tier,
        bounty_issue=bounty_issue,
    )
    return result


@router.get("/history", response_model=SpamHistoryResponse)
async def spam_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get spam check history (newest first)."""
    return spam_detector.get_history(skip=skip, limit=limit)


@router.get("/stats", response_model=SpamStatsResponse)
async def spam_stats():
    """Get spam detection statistics."""
    return spam_detector.get_stats()


@router.patch("/config", response_model=SpamConfigResponse)
async def update_spam_config(
    body: SpamConfigUpdate,
    authorization: Optional[str] = Header(None),
):
    """Update spam detection thresholds (admin only)."""
    _verify_admin(authorization)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    return spam_detector.update_config(updates)


@router.get("/config", response_model=SpamConfigResponse)
async def get_spam_config():
    """Get current spam detection configuration."""
    return spam_detector.get_config()
