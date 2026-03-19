"""Reputation API endpoints.

Provides REST access to on-chain reputation scores, history, leaderboard,
eligibility checks, and sync operations.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.reputation import (
    BountyTier,
    EligibilityResponse,
    LeaderboardEntry,
    ReputationHistoryResponse,
    ReputationLeaderboardResponse,
    ReputationResponse,
    ReputationTier,
    SyncRequest,
    SyncResponse,
)
from app.services.reputation_integration import ReputationIntegrationService
from app.services.reputation_sdk import ReputationSDK

router = APIRouter(prefix="/api/reputation", tags=["reputation"])

# ---------------------------------------------------------------------------
# Service singleton — initialised lazily so tests can swap the SDK.
# ---------------------------------------------------------------------------

_service: Optional[ReputationIntegrationService] = None


def _get_service() -> ReputationIntegrationService:
    global _service  # noqa: PLW0603
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail="Reputation service not initialised. Call init_reputation_service() first.",
        )
    return _service


def init_reputation_service(sdk: ReputationSDK) -> ReputationIntegrationService:
    """Initialise (or replace) the module-level service singleton."""
    global _service  # noqa: PLW0603
    _service = ReputationIntegrationService(sdk)
    return _service


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{wallet}", response_model=ReputationResponse)
async def get_reputation(wallet: str):
    """Get on-chain reputation score for a wallet."""
    svc = _get_service()
    score = svc.get_score(wallet)
    return ReputationResponse(
        wallet=score.wallet,
        score=score.score,
        tier=score.tier,
        last_updated=score.last_updated,
    )


@router.get("/{wallet}/history", response_model=ReputationHistoryResponse)
async def get_reputation_history(
    wallet: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Reputation change history for a wallet."""
    svc = _get_service()
    items, total = svc.get_history(wallet, limit=limit, offset=offset)
    return ReputationHistoryResponse(items=items, total=total)


@router.get("/{wallet}/eligibility", response_model=EligibilityResponse)
async def check_eligibility(
    wallet: str,
    bounty_tier: int = Query(..., ge=1, le=3, description="Bounty tier (1, 2, or 3)"),
):
    """Check whether a wallet is eligible to claim a bounty of the given tier."""
    svc = _get_service()
    tier = BountyTier(bounty_tier)
    result = await svc.check_eligibility(wallet, tier)
    return EligibilityResponse(
        wallet=result.wallet,
        bounty_tier=result.bounty_tier,
        eligible=result.eligible,
        reputation_score=result.reputation_score,
        reputation_tier=result.reputation_tier,
        meets_reputation=result.meets_reputation,
        meets_token_gate=result.meets_token_gate,
        cooldown_active=result.cooldown_active,
        cooldown_expires_at=result.cooldown_expires_at,
        reasons=result.reasons,
    )


@router.get("/leaderboard/", response_model=ReputationLeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Top contributors by on-chain reputation score."""
    svc = _get_service()
    scores, total = svc.get_leaderboard(limit=limit, offset=offset)
    items = [
        LeaderboardEntry(
            rank=offset + idx + 1,
            wallet=s.wallet,
            score=s.score,
            tier=s.tier,
        )
        for idx, s in enumerate(scores)
    ]
    return ReputationLeaderboardResponse(items=items, total=total)


@router.post("/sync", response_model=SyncResponse)
async def sync_reputation(body: SyncRequest):
    """Sync on-chain reputation with the platform DB.

    If ``wallets`` is provided, only those wallets are synced; otherwise every
    known wallet is refreshed.
    """
    svc = _get_service()
    if body.wallets:
        errors: list[str] = []
        synced = 0
        for w in body.wallets:
            try:
                await svc.sync_wallet(w)
                synced += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{w}: {exc}")
        return SyncResponse(synced=synced, errors=errors)

    synced, errors = await svc.sync_all()
    return SyncResponse(synced=synced, errors=errors)
