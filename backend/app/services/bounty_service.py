"""In-memory bounty service for MVP."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.bounty import (
    BountyCreate,
    BountyDB,
    BountyListItem,
    BountyListResponse,
    BountyResponse,
    BountyStatus,
    BountyTier,
    BountyUpdate,
    ClaimRecord,
    ClaimResponse,
    ClaimStatus,
    SubmissionResponse,
    TIER_DEADLINE_DAYS,
    TIER_REP_REQUIREMENTS,
)

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_bounty_store: dict[str, BountyDB] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _effective_min_rep(bounty: BountyDB) -> int:
    """Return the effective minimum reputation for a bounty."""
    if bounty.min_reputation is not None:
        return bounty.min_reputation
    return TIER_REP_REQUIREMENTS.get(bounty.tier, 0)


def _claim_to_response(claim: ClaimRecord) -> ClaimResponse:
    return ClaimResponse(
        id=claim.id,
        bounty_id=claim.bounty_id,
        contributor_id=claim.contributor_id,
        status=claim.status,
        application_text=claim.application_text,
        claimed_at=claim.claimed_at,
        deadline=claim.deadline,
        released_at=claim.released_at,
        completed_at=claim.completed_at,
    )


def _bounty_to_response(bounty: BountyDB) -> BountyResponse:
    active_claim = None
    if bounty.active_claim_id:
        for c in bounty.claim_history:
            if c.id == bounty.active_claim_id:
                active_claim = _claim_to_response(c)
                break

    submissions = [
        SubmissionResponse(
            id=s.id, bounty_id=s.bounty_id, pr_url=s.pr_url,
            submitted_by=s.submitted_by, notes=s.notes, submitted_at=s.submitted_at,
        )
        for s in bounty.submissions
    ]

    return BountyResponse(
        id=bounty.id,
        title=bounty.title,
        description=bounty.description,
        tier=bounty.tier,
        reward_amount=bounty.reward_amount,
        status=bounty.status,
        github_issue_url=bounty.github_issue_url,
        required_skills=bounty.required_skills,
        deadline=bounty.deadline,
        min_reputation=_effective_min_rep(bounty),
        created_by=bounty.created_by,
        active_claim=active_claim,
        claim_count=len(bounty.claim_history),
        submissions=submissions,
        submission_count=len(bounty.submissions),
        created_at=bounty.created_at,
        updated_at=bounty.updated_at,
    )


def _bounty_to_list_item(bounty: BountyDB) -> BountyListItem:
    return BountyListItem(
        id=bounty.id,
        title=bounty.title,
        tier=bounty.tier,
        reward_amount=bounty.reward_amount,
        status=bounty.status,
        required_skills=bounty.required_skills,
        deadline=bounty.deadline,
        created_by=bounty.created_by,
        submission_count=len(bounty.submissions),
        claim_count=len(bounty.claim_history),
        created_at=bounty.created_at,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_bounty(data: BountyCreate) -> BountyResponse:
    bounty = BountyDB(
        title=data.title,
        description=data.description,
        tier=data.tier,
        reward_amount=data.reward_amount,
        github_issue_url=data.github_issue_url,
        required_skills=data.required_skills,
        deadline=data.deadline,
        min_reputation=data.min_reputation,
        created_by=data.created_by,
    )
    _bounty_store[bounty.id] = bounty
    return _bounty_to_response(bounty)


def get_bounty(bounty_id: str) -> Optional[BountyResponse]:
    bounty = _bounty_store.get(bounty_id)
    return _bounty_to_response(bounty) if bounty else None


def get_bounty_db(bounty_id: str) -> Optional[BountyDB]:
    return _bounty_store.get(bounty_id)


def list_bounties(
    status: Optional[BountyStatus] = None,
    tier: Optional[BountyTier] = None,
    skip: int = 0,
    limit: int = 20,
) -> BountyListResponse:
    results = list(_bounty_store.values())
    if status:
        results = [b for b in results if b.status == status]
    if tier:
        results = [b for b in results if b.tier == tier]
    total = len(results)
    return BountyListResponse(
        items=[_bounty_to_list_item(b) for b in results[skip: skip + limit]],
        total=total,
        skip=skip,
        limit=limit,
    )


def update_bounty(bounty_id: str, data: BountyUpdate) -> Optional[BountyResponse]:
    bounty = _bounty_store.get(bounty_id)
    if not bounty:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(bounty, key, value)
    bounty.updated_at = datetime.now(timezone.utc)
    return _bounty_to_response(bounty)


def delete_bounty(bounty_id: str) -> bool:
    return _bounty_store.pop(bounty_id, None) is not None


# ---------------------------------------------------------------------------
# Claiming
# ---------------------------------------------------------------------------

def claim_bounty(
    bounty_id: str,
    contributor_id: str,
    contributor_reputation: int,
    application_text: Optional[str] = None,
) -> tuple[Optional[ClaimResponse], Optional[str]]:
    """Attempt to claim a bounty.

    Returns (ClaimResponse, None) on success or (None, error_message) on failure.
    """
    bounty = _bounty_store.get(bounty_id)
    if not bounty:
        return None, "Bounty not found"

    # Must be open
    if bounty.status != BountyStatus.OPEN:
        return None, f"Bounty is not available for claiming (status: {bounty.status.value})"

    # Tier 1 bounties don't use the claim system
    if bounty.tier == BountyTier.T1:
        return None, "Tier 1 bounties do not require claiming"

    # Reputation gate
    min_rep = _effective_min_rep(bounty)
    if contributor_reputation < min_rep:
        return None, f"Insufficient reputation ({contributor_reputation} < {min_rep} required)"

    # Check contributor doesn't already have an active claim on ANY bounty
    for b in _bounty_store.values():
        for c in b.claim_history:
            if c.contributor_id == contributor_id and c.status in (ClaimStatus.ACTIVE, ClaimStatus.PENDING):
                return None, f"You already have an active claim on bounty {b.id}"

    # T3 requires application text
    if bounty.tier == BountyTier.T3 and not application_text:
        return None, "Tier 3 bounties require an application with a plan"

    # Compute deadline
    deadline_days = TIER_DEADLINE_DAYS.get(bounty.tier, 7)
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=deadline_days) if deadline_days > 0 else None

    # Determine initial claim status
    initial_status = ClaimStatus.ACTIVE
    if bounty.tier == BountyTier.T3:
        initial_status = ClaimStatus.PENDING  # needs admin approval

    claim = ClaimRecord(
        bounty_id=bounty_id,
        contributor_id=contributor_id,
        status=initial_status,
        application_text=application_text,
        claimed_at=now,
        deadline=deadline,
    )
    bounty.claim_history.append(claim)

    if initial_status == ClaimStatus.ACTIVE:
        bounty.active_claim_id = claim.id
        bounty.status = BountyStatus.IN_PROGRESS

    bounty.updated_at = now
    return _claim_to_response(claim), None


def unclaim_bounty(
    bounty_id: str,
    contributor_id: str,
) -> tuple[Optional[ClaimResponse], Optional[str]]:
    """Voluntarily release a claim.

    Returns (ClaimResponse, None) on success or (None, error_message) on failure.
    """
    bounty = _bounty_store.get(bounty_id)
    if not bounty:
        return None, "Bounty not found"

    # Find the contributor's active/pending claim
    claim = None
    for c in bounty.claim_history:
        if c.contributor_id == contributor_id and c.status in (ClaimStatus.ACTIVE, ClaimStatus.PENDING):
            claim = c
            break

    if not claim:
        return None, "No active claim found for this contributor on this bounty"

    now = datetime.now(timezone.utc)
    claim.status = ClaimStatus.RELEASED
    claim.released_at = now

    if bounty.active_claim_id == claim.id:
        bounty.active_claim_id = None
        bounty.status = BountyStatus.OPEN

    # If no active claim, ensure bounty is open
    if not bounty.active_claim_id:
        bounty.status = BountyStatus.OPEN

    bounty.updated_at = now
    return _claim_to_response(claim), None


def approve_claim(
    bounty_id: str,
    claim_id: str,
) -> tuple[Optional[ClaimResponse], Optional[str]]:
    """Admin approves a T3 application."""
    bounty = _bounty_store.get(bounty_id)
    if not bounty:
        return None, "Bounty not found"

    claim = None
    for c in bounty.claim_history:
        if c.id == claim_id:
            claim = c
            break

    if not claim:
        return None, "Claim not found"

    if claim.status != ClaimStatus.PENDING:
        return None, f"Claim is not pending (status: {claim.status})"

    now = datetime.now(timezone.utc)
    claim.status = ClaimStatus.ACTIVE
    # Reset deadline from approval time
    deadline_days = TIER_DEADLINE_DAYS.get(bounty.tier, 14)
    claim.deadline = now + timedelta(days=deadline_days)

    bounty.active_claim_id = claim.id
    bounty.status = BountyStatus.IN_PROGRESS
    bounty.updated_at = now

    return _claim_to_response(claim), None


def reject_claim(
    bounty_id: str,
    claim_id: str,
) -> tuple[Optional[ClaimResponse], Optional[str]]:
    """Admin rejects a T3 application."""
    bounty = _bounty_store.get(bounty_id)
    if not bounty:
        return None, "Bounty not found"

    claim = None
    for c in bounty.claim_history:
        if c.id == claim_id:
            claim = c
            break

    if not claim:
        return None, "Claim not found"

    if claim.status != ClaimStatus.PENDING:
        return None, f"Claim is not pending (status: {claim.status})"

    claim.status = ClaimStatus.REJECTED
    bounty.updated_at = datetime.now(timezone.utc)

    return _claim_to_response(claim), None


def get_claim_history(bounty_id: str) -> Optional[list[ClaimResponse]]:
    bounty = _bounty_store.get(bounty_id)
    if not bounty:
        return None
    return [_claim_to_response(c) for c in bounty.claim_history]


def get_contributor_claims(contributor_id: str) -> list[ClaimResponse]:
    """Get all claims by a specific contributor across all bounties."""
    claims: list[ClaimResponse] = []
    for bounty in _bounty_store.values():
        for c in bounty.claim_history:
            if c.contributor_id == contributor_id:
                claims.append(_claim_to_response(c))
    return claims


# ---------------------------------------------------------------------------
# Deadline watcher
# ---------------------------------------------------------------------------

def check_expired_claims() -> list[ClaimResponse]:
    """Scan all bounties for expired claims and release them.

    Returns list of claims that were expired.
    """
    now = datetime.now(timezone.utc)
    expired: list[ClaimResponse] = []

    for bounty in _bounty_store.values():
        for claim in bounty.claim_history:
            if claim.status == ClaimStatus.ACTIVE and claim.deadline and claim.deadline <= now:
                claim.status = ClaimStatus.EXPIRED
                claim.released_at = now
                if bounty.active_claim_id == claim.id:
                    bounty.active_claim_id = None
                    bounty.status = BountyStatus.OPEN
                bounty.updated_at = now
                expired.append(_claim_to_response(claim))

    return expired
