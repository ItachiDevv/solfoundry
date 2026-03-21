"""Bounty review flow API: submit -> scores -> approve/dispute -> payout."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.review import (AutoApproveResult, ReviewApproveRequest,
    ReviewDisputeRequest, ReviewListItem, ReviewResponse,
    ReviewScoresCreate, ReviewStatus, ReviewSubmitCreate)
from app.services import review_service

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _ok(result, error):
    """Raise HTTPException on error, return result on success."""
    if error:
        raise HTTPException(status_code=404 if "not found" in error.lower() else 400, detail=error)
    return result


@router.post("/bounties/{bounty_id}/submit", response_model=ReviewResponse, status_code=201,
             summary="Submit a PR for review on a bounty")
async def submit_for_review(bounty_id: str, data: ReviewSubmitCreate) -> ReviewResponse:
    """Submit a PR for AI review, linking it to the bounty."""
    return _ok(*review_service.submit_for_review(bounty_id, data))


@router.post("/bounties/{bounty_id}/scores", response_model=ReviewResponse,
             summary="Record AI review scores from GitHub Actions")
async def record_scores(bounty_id: str, data: ReviewScoresCreate) -> ReviewResponse:
    """Record per-model AI scores and check against tier threshold."""
    return _ok(*review_service.record_review_scores(bounty_id, data))


@router.post("/bounties/{bounty_id}/approve", response_model=ReviewResponse,
             summary="Creator approves a reviewed submission")
async def approve(bounty_id: str, data: ReviewApproveRequest) -> ReviewResponse:
    """Creator approves, triggering $FNDRY payout to contributor."""
    return _ok(*review_service.approve_submission(bounty_id, data))


@router.post("/bounties/{bounty_id}/dispute", response_model=ReviewResponse,
             summary="Creator disputes a reviewed submission")
async def dispute(bounty_id: str, data: ReviewDisputeRequest) -> ReviewResponse:
    """Creator disputes submission, preventing auto-approval."""
    return _ok(*review_service.dispute_submission(bounty_id, data))


@router.get("/bounties/{bounty_id}", response_model=ReviewResponse,
            summary="Get review status and scores for a bounty")
async def get_review(bounty_id: str) -> ReviewResponse:
    """Get per-model scores, approval status, and lifecycle log."""
    r = review_service.get_review(bounty_id)
    if not r:
        raise HTTPException(status_code=404, detail="No review found for this bounty")
    return r


@router.get("", response_model=list[ReviewListItem], summary="List reviews")
async def list_reviews(
    status: Optional[ReviewStatus] = Query(None), skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)) -> list[ReviewListItem]:
    """List reviews with optional status filter and pagination."""
    return review_service.list_reviews(status=status, skip=skip, limit=limit)


@router.post("/auto-approve", response_model=AutoApproveResult,
             summary="Trigger auto-approve check")
async def auto_approve() -> AutoApproveResult:
    """Auto-approve scored reviews meeting threshold after 48h."""
    return review_service.check_auto_approve()
