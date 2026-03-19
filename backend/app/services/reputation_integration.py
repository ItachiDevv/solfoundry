"""Bridge between platform events and the on-chain reputation system.

Handles PR merge / rejection events, cooldown enforcement, sybil checks,
and keeps the platform DB in sync with on-chain state.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.reputation import (
    REJECTION_THRESHOLD,
    MIN_FNDRY_FOR_TIER,
    MIN_REPUTATION_FOR_TIER,
    TIER_COOLDOWN_HOURS,
    TIER_REPUTATION_REWARDS,
    BountyTier,
    CooldownRecord,
    EligibilityCheck,
    ReputationChangeReason,
    ReputationHistory,
    ReputationScore,
    ReputationTier,
)
from app.services.reputation_sdk import ReputationSDK

logger = logging.getLogger(__name__)


class ReputationIntegrationService:
    """Orchestrates reputation updates in response to platform events."""

    def __init__(self, sdk: ReputationSDK) -> None:
        self.sdk = sdk

        # In-memory stores (swap for DB in production)
        self._scores: dict[str, ReputationScore] = {}
        self._history: dict[str, list[ReputationHistory]] = {}
        self._cooldowns: dict[str, list[CooldownRecord]] = {}
        self._rejection_counts: dict[str, int] = {}  # wallet -> consecutive rejections

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def on_pr_merged(
        self,
        wallet: str,
        bounty_tier: BountyTier,
        *,
        pr_url: Optional[str] = None,
    ) -> ReputationHistory:
        """Called when a contributor's PR is merged.

        Awards reputation points based on the bounty tier.
        """
        delta = TIER_REPUTATION_REWARDS[bounty_tier]

        # Ensure PDA exists
        await self.sdk.initialize_reputation(wallet)

        # Push update on-chain
        tx_sig = await self.sdk.update_reputation(wallet, delta)

        # Reset consecutive rejection counter on success
        self._rejection_counts[wallet] = 0

        # Record locally
        entry = ReputationHistory(
            wallet=wallet,
            delta=delta,
            reason=ReputationChangeReason.PR_MERGED,
            bounty_tier=bounty_tier,
            tx_signature=tx_sig,
            metadata={"pr_url": pr_url} if pr_url else {},
        )
        self._append_history(wallet, entry)
        await self._sync_score(wallet)
        return entry

    async def on_pr_rejected(
        self,
        wallet: str,
        bounty_tier: BountyTier,
        *,
        pr_url: Optional[str] = None,
    ) -> Optional[ReputationHistory]:
        """Called when a contributor's PR is rejected.

        Increments the rejection counter. On the 3rd consecutive rejection,
        decrements reputation and applies a cooldown.
        """
        count = self._rejection_counts.get(wallet, 0) + 1
        self._rejection_counts[wallet] = count

        if count < REJECTION_THRESHOLD:
            logger.info(
                "Wallet %s rejection %d/%d — no penalty yet",
                wallet, count, REJECTION_THRESHOLD,
            )
            return None

        # Penalty: decrement reputation
        delta = -TIER_REPUTATION_REWARDS[bounty_tier]
        await self.sdk.initialize_reputation(wallet)
        tx_sig = await self.sdk.update_reputation(wallet, delta)

        # Apply cooldown
        cooldown_hours = TIER_COOLDOWN_HOURS[bounty_tier]
        now = datetime.now(timezone.utc)
        cooldown = CooldownRecord(
            wallet=wallet,
            bounty_tier=bounty_tier,
            reason="consecutive_rejections",
            started_at=now,
            expires_at=now + timedelta(hours=cooldown_hours),
        )
        self._cooldowns.setdefault(wallet, []).append(cooldown)

        # Reset counter
        self._rejection_counts[wallet] = 0

        entry = ReputationHistory(
            wallet=wallet,
            delta=delta,
            reason=ReputationChangeReason.PR_REJECTED,
            bounty_tier=bounty_tier,
            tx_signature=tx_sig,
            metadata={
                "pr_url": pr_url,
                "cooldown_hours": cooldown_hours,
            },
        )
        self._append_history(wallet, entry)
        await self._sync_score(wallet)
        return entry

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    async def check_eligibility(
        self, wallet: str, bounty_tier: BountyTier,
    ) -> EligibilityCheck:
        """Determine whether *wallet* may claim a bounty of *bounty_tier*."""
        reasons: list[str] = []

        # 1. On-chain reputation
        on_chain = await self.sdk.get_reputation(wallet)
        score = on_chain.score
        rep_tier = ReputationTier.from_score(score)
        min_rep = MIN_REPUTATION_FOR_TIER[bounty_tier]
        meets_reputation = score >= min_rep
        if not meets_reputation:
            reasons.append(
                f"Reputation {score} below minimum {min_rep} for T{bounty_tier.value}"
            )

        # 2. Token gate ($FNDRY balance)
        min_fndry = MIN_FNDRY_FOR_TIER[bounty_tier]
        meets_token_gate = True
        if min_fndry > 0:
            balance = await self.sdk.get_token_balance(wallet)
            meets_token_gate = balance >= min_fndry
            if not meets_token_gate:
                reasons.append(
                    f"$FNDRY balance {balance:.2f} below minimum {min_fndry:.2f} for T{bounty_tier.value}"
                )

        # 3. Cooldown
        cooldown_active = False
        cooldown_expires: Optional[datetime] = None
        now = datetime.now(timezone.utc)
        for cd in self._cooldowns.get(wallet, []):
            if cd.active and cd.expires_at > now and cd.bounty_tier == bounty_tier:
                cooldown_active = True
                cooldown_expires = cd.expires_at
                reasons.append(
                    f"Cooldown active until {cd.expires_at.isoformat()} for T{bounty_tier.value}"
                )
                break

        eligible = meets_reputation and meets_token_gate and not cooldown_active

        return EligibilityCheck(
            wallet=wallet,
            bounty_tier=bounty_tier,
            eligible=eligible,
            reputation_score=score,
            reputation_tier=rep_tier,
            meets_reputation=meets_reputation,
            meets_token_gate=meets_token_gate,
            cooldown_active=cooldown_active,
            cooldown_expires_at=cooldown_expires,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_score(self, wallet: str) -> ReputationScore:
        return self._scores.get(wallet, ReputationScore(wallet=wallet))

    def get_history(
        self, wallet: str, *, limit: int = 50, offset: int = 0,
    ) -> tuple[list[ReputationHistory], int]:
        items = self._history.get(wallet, [])
        total = len(items)
        # Return newest first
        sorted_items = sorted(items, key=lambda h: h.created_at, reverse=True)
        return sorted_items[offset: offset + limit], total

    def get_leaderboard(
        self, *, limit: int = 20, offset: int = 0,
    ) -> tuple[list[ReputationScore], int]:
        all_scores = sorted(
            self._scores.values(), key=lambda s: s.score, reverse=True,
        )
        total = len(all_scores)
        return all_scores[offset: offset + limit], total

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    async def sync_wallet(self, wallet: str) -> ReputationScore:
        """Pull the latest on-chain score and update local state."""
        self.sdk.invalidate_cache(wallet)
        await self._sync_score(wallet)
        return self._scores[wallet]

    async def sync_all(self) -> tuple[int, list[str]]:
        """Sync every known wallet. Returns (success_count, errors)."""
        errors: list[str] = []
        count = 0
        for wallet in list(self._scores.keys()):
            try:
                await self.sync_wallet(wallet)
                count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{wallet}: {exc}")
        return count, errors

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_history(self, wallet: str, entry: ReputationHistory) -> None:
        self._history.setdefault(wallet, []).append(entry)

    async def _sync_score(self, wallet: str) -> None:
        on_chain = await self.sdk.get_reputation(wallet)
        score_obj = self._scores.get(wallet, ReputationScore(wallet=wallet))
        score_obj.score = on_chain.score
        score_obj.recalculate_tier()
        score_obj.last_updated = datetime.now(timezone.utc)
        self._scores[wallet] = score_obj
