"""Bounty completion and review flow service (in-memory MVP).

Submit PR -> AI scores -> creator approve/dispute -> auto-approve
after 48h -> payout -> bounty complete. All transitions logged.

PostgreSQL migration: ReviewRecord -> 'reviews' table, JSONB for
scores and lifecycle_log. See models/review.py.
"""

import threading, uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.models.bounty import BountyStatus, BountyUpdate
from app.models.payout import PayoutCreate
from app.models.review import (
    AUTO_APPROVE_HOURS, REVIEW_TIER_THRESHOLDS, ReviewApproveRequest,
    ReviewDisputeRequest, ReviewListItem, ReviewRecord, ReviewResponse,
    ReviewScoresCreate, ReviewStatus, ReviewSubmitCreate, AutoApproveResult)
from app.services import bounty_service
from app.services.payout_service import create_payout

_lock = threading.Lock()
_review_store: dict[str, ReviewRecord] = {}


def _log(r: ReviewRecord, action: str, actor: Optional[str] = None) -> None:
    """Append lifecycle event to audit log."""
    r.lifecycle_log.append({"action": action, "actor": actor or "system",
        "status": r.status.value, "timestamp": datetime.now(timezone.utc).isoformat()})
    r.updated_at = datetime.now(timezone.utc)


def _resp(r: ReviewRecord) -> ReviewResponse:
    """Convert ReviewRecord to API response."""
    return ReviewResponse.model_validate(r)


def _find(bounty_id: str) -> Optional[ReviewRecord]:
    """Find most recent review for a bounty."""
    with _lock:
        cands = [r for r in _review_store.values() if r.bounty_id == bounty_id]
    return max(cands, key=lambda r: r.created_at) if cands else None


def _pay(review: ReviewRecord) -> None:
    """Trigger payout for an approved review."""
    bounty = bounty_service.get_bounty(review.bounty_id)
    if not bounty:
        return
    try:
        create_payout(PayoutCreate(recipient=review.submitted_by,
            recipient_wallet=review.contributor_wallet, amount=bounty.reward_amount,
            token="FNDRY", bounty_id=review.bounty_id, bounty_title=bounty.title))
        with _lock:
            review.payout_amount = bounty.reward_amount
            review.winner_wallet = review.contributor_wallet
            review.status = ReviewStatus.PAID
            _log(review, f"Payout created: {bounty.reward_amount} FNDRY to {review.contributor_wallet}")
        bounty_service.update_bounty(review.bounty_id, BountyUpdate(status=BountyStatus.COMPLETED))
        bounty_service.update_bounty(review.bounty_id, BountyUpdate(status=BountyStatus.PAID))
    except Exception as err:
        with _lock:
            _log(review, f"Payout failed: {err}")


def submit_for_review(bounty_id: str, data: ReviewSubmitCreate
                      ) -> tuple[Optional[ReviewResponse], Optional[str]]:
    """Submit a PR for review, linking it to the bounty."""
    bounty = bounty_service.get_bounty(bounty_id)
    if not bounty:
        return None, "Bounty not found"
    if bounty.status not in (BountyStatus.OPEN, BountyStatus.IN_PROGRESS):
        return None, f"Bounty not accepting submissions (status: {bounty.status.value})"
    with _lock:
        for r in _review_store.values():
            if r.bounty_id == bounty_id and r.pr_url == data.pr_url:
                return None, "This PR already submitted for review on this bounty"
    review = ReviewRecord(bounty_id=bounty_id, submission_id=str(uuid.uuid4()),
        pr_url=data.pr_url, contributor_wallet=data.contributor_wallet,
        submitted_by=data.submitted_by, notes=data.notes, status=ReviewStatus.IN_REVIEW)
    _log(review, "PR submitted for review", data.submitted_by)
    if bounty.status == BountyStatus.OPEN:
        bounty_service.update_bounty(bounty_id, BountyUpdate(status=BountyStatus.IN_PROGRESS))
    with _lock:
        _review_store[review.id] = review
    return _resp(review), None


def record_review_scores(bounty_id: str, data: ReviewScoresCreate
                         ) -> tuple[Optional[ReviewResponse], Optional[str]]:
    """Record AI review scores from GitHub Actions."""
    review = _find(bounty_id)
    if not review:
        return None, "Review not found for this bounty"
    if review.status != ReviewStatus.IN_REVIEW:
        return None, f"Not in reviewable state (status: {review.status.value})"
    for s in data.scores:
        s.model_average = s.compute_average()
    bounty = bounty_service.get_bounty(bounty_id)
    threshold = REVIEW_TIER_THRESHOLDS.get(bounty.tier if bounty else 2, 7.0)
    overall = round(sum(s.model_average for s in data.scores) / len(data.scores), 2)
    with _lock:
        review.scores = data.scores
        review.overall_score = overall
        review.meets_threshold = overall >= threshold
        review.status = ReviewStatus.SCORED
        review.scored_at = datetime.now(timezone.utc)
        _log(review, f"AI review scored: {overall}/10 (threshold: {threshold})")
    return _resp(review), None


def approve_submission(bounty_id: str, data: ReviewApproveRequest
                       ) -> tuple[Optional[ReviewResponse], Optional[str]]:
    """Creator approves submission, triggering payout."""
    review = _find(bounty_id)
    if not review:
        return None, "Review not found for this bounty"
    if review.status not in (ReviewStatus.SCORED, ReviewStatus.IN_REVIEW):
        return None, f"Cannot approve (status: {review.status.value})"
    with _lock:
        review.status = ReviewStatus.APPROVED
        review.approved_by = data.approved_by
        review.approved_at = datetime.now(timezone.utc)
        _log(review, "Submission approved by creator", data.approved_by)
    _pay(review)
    return _resp(review), None


def dispute_submission(bounty_id: str, data: ReviewDisputeRequest
                       ) -> tuple[Optional[ReviewResponse], Optional[str]]:
    """Creator disputes submission, preventing auto-approval."""
    review = _find(bounty_id)
    if not review:
        return None, "Review not found for this bounty"
    if review.status != ReviewStatus.SCORED:
        return None, f"Cannot dispute (status: {review.status.value})"
    with _lock:
        review.status = ReviewStatus.DISPUTED
        review.disputed_by = data.disputed_by
        review.dispute_reason = data.reason
        review.disputed_at = datetime.now(timezone.utc)
        _log(review, f"Submission disputed: {data.reason}", data.disputed_by)
    return _resp(review), None


def get_review(bounty_id: str) -> Optional[ReviewResponse]:
    """Get the current review for a bounty."""
    r = _find(bounty_id)
    return _resp(r) if r else None


def list_reviews(status: Optional[ReviewStatus] = None, skip: int = 0,
                 limit: int = 20) -> list[ReviewListItem]:
    """List reviews with optional status filter."""
    with _lock:
        results = sorted(_review_store.values(), key=lambda r: r.created_at, reverse=True)
    if status is not None:
        results = [r for r in results if r.status == status]
    return [ReviewListItem(id=r.id, bounty_id=r.bounty_id, pr_url=r.pr_url,
        submitted_by=r.submitted_by, status=r.status, overall_score=r.overall_score,
        meets_threshold=r.meets_threshold, created_at=r.created_at)
        for r in results[skip:skip + limit]]


def check_auto_approve() -> AutoApproveResult:
    """Check SCORED reviews for 48h auto-approval."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=AUTO_APPROVE_HOURS)
    result = AutoApproveResult()
    with _lock:
        cands = [r for r in _review_store.values() if r.status == ReviewStatus.SCORED]
    for review in cands:
        result.checked_count += 1
        if not review.meets_threshold:
            result.details.append({"review_id": review.id, "bounty_id": review.bounty_id,
                                   "action": "skipped", "reason": "Score below threshold"})
        elif review.scored_at and review.scored_at <= cutoff:
            with _lock:
                review.status = ReviewStatus.APPROVED
                review.approved_by = "auto-approve"
                review.approved_at = now
                _log(review, "Auto-approved after 48h timeout", "system")
            _pay(review)
            result.approved_count += 1
            result.details.append({"review_id": review.id, "bounty_id": review.bounty_id,
                                   "action": "approved", "reason": "Threshold met, 48h elapsed"})
        else:
            result.details.append({"review_id": review.id, "bounty_id": review.bounty_id,
                                   "action": "waiting", "reason": "48h not yet elapsed"})
    return result


def reset_store() -> None:
    """Clear all in-memory review data. Used by tests."""
    with _lock:
        _review_store.clear()
