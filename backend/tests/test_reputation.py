"""Tests for the on-chain reputation system (Phase 6).

Covers:
  - ReputationSDK with mocked Solana RPC
  - ReputationIntegrationService event handling
  - Eligibility checks (reputation gate, token gate, cooldowns)
  - API endpoints via FastAPI TestClient
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.reputation import (
    BountyTier,
    EligibilityCheck,
    MIN_FNDRY_FOR_TIER,
    MIN_REPUTATION_FOR_TIER,
    REJECTION_THRESHOLD,
    ReputationChangeReason,
    ReputationTier,
    TIER_REPUTATION_REWARDS,
)
from app.services.reputation_integration import ReputationIntegrationService
from app.services.reputation_sdk import (
    OnChainReputation,
    ReputationSDK,
    derive_reputation_pda,
)


# ---------------------------------------------------------------------------
# Mock Solana client
# ---------------------------------------------------------------------------

class MockSolanaClient:
    """In-memory mock that implements the SolanaClient protocol."""

    def __init__(
        self,
        *,
        preset_balance: float = 1000.0,
        fail_on_send: bool = False,
    ) -> None:
        self.accounts: dict[str, dict] = {}
        self.preset_balance = preset_balance
        self.fail_on_send = fail_on_send
        self.tx_count = 0

    async def get_account_info(self, pubkey: str) -> Optional[dict]:
        return self.accounts.get(pubkey)

    async def send_transaction(self, tx_data: dict) -> str:
        if self.fail_on_send:
            raise RuntimeError("Simulated RPC failure")
        self.tx_count += 1
        instruction = tx_data.get("instruction", "unknown")
        if instruction == "initialize":
            pda = tx_data["accounts"]["reputation"]
            self.accounts[pda] = {"score": 0, "bump": 255}
        elif instruction == "update_reputation":
            pda = tx_data["accounts"]["reputation"]
            if pda in self.accounts:
                delta = tx_data.get("data", {}).get("delta", 0)
                self.accounts[pda]["score"] = max(
                    0, self.accounts[pda].get("score", 0) + delta,
                )
        return f"mock_sig_{self.tx_count}"

    async def get_token_balance(self, wallet: str, mint: str) -> float:
        return self.preset_balance


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WALLET_A = "WalletAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "WalletBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


@pytest.fixture
def mock_client() -> MockSolanaClient:
    return MockSolanaClient()


@pytest.fixture
def sdk(mock_client: MockSolanaClient) -> ReputationSDK:
    return ReputationSDK(client=mock_client)


@pytest.fixture
def service(sdk: ReputationSDK) -> ReputationIntegrationService:
    return ReputationIntegrationService(sdk)


@pytest.fixture
def api_service(sdk: ReputationSDK):
    """Initialise the API module's singleton and tear it down after the test."""
    from app.api import reputation as rep_api
    svc = rep_api.init_reputation_service(sdk)
    yield svc
    rep_api._service = None


# ---------------------------------------------------------------------------
# SDK tests
# ---------------------------------------------------------------------------

class TestReputationSDK:
    def test_derive_pda_deterministic(self):
        pda1 = derive_reputation_pda(WALLET_A)
        pda2 = derive_reputation_pda(WALLET_A)
        assert pda1 == pda2

    def test_derive_pda_unique_per_wallet(self):
        assert derive_reputation_pda(WALLET_A) != derive_reputation_pda(WALLET_B)

    @pytest.mark.asyncio
    async def test_initialize_reputation(self, sdk: ReputationSDK):
        sig = await sdk.initialize_reputation(WALLET_A)
        assert sig.startswith("mock_sig_")
        rep = await sdk.get_reputation(WALLET_A)
        assert rep.initialized is True
        assert rep.score == 0

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, sdk: ReputationSDK):
        await sdk.initialize_reputation(WALLET_A)
        sig2 = await sdk.initialize_reputation(WALLET_A)
        assert sig2 == "already_initialized"

    @pytest.mark.asyncio
    async def test_update_reputation_positive(self, sdk: ReputationSDK):
        await sdk.initialize_reputation(WALLET_A)
        await sdk.update_reputation(WALLET_A, 10)
        rep = await sdk.get_reputation(WALLET_A)
        assert rep.score == 10

    @pytest.mark.asyncio
    async def test_update_reputation_negative_clamp(self, sdk: ReputationSDK):
        await sdk.initialize_reputation(WALLET_A)
        await sdk.update_reputation(WALLET_A, 5)
        await sdk.update_reputation(WALLET_A, -20)
        rep = await sdk.get_reputation(WALLET_A)
        assert rep.score == 0  # clamped at 0

    @pytest.mark.asyncio
    async def test_get_reputation_uninitialised(self, sdk: ReputationSDK):
        rep = await sdk.get_reputation("NonExistentWallet")
        assert rep.initialized is False
        assert rep.score == 0

    @pytest.mark.asyncio
    async def test_batch_update(self, sdk: ReputationSDK):
        await sdk.initialize_reputation(WALLET_A)
        await sdk.initialize_reputation(WALLET_B)
        results = await sdk.batch_update([(WALLET_A, 5), (WALLET_B, 10)])
        assert len(results) == 2
        assert all(sig.startswith("mock_sig_") for _, sig in results)
        rep_a = await sdk.get_reputation(WALLET_A)
        rep_b = await sdk.get_reputation(WALLET_B)
        assert rep_a.score == 5
        assert rep_b.score == 10

    @pytest.mark.asyncio
    async def test_batch_update_partial_failure(self):
        client = MockSolanaClient()
        sdk = ReputationSDK(client=client)
        await sdk.initialize_reputation(WALLET_A)
        # Make subsequent sends fail
        client.fail_on_send = True
        results = await sdk.batch_update([(WALLET_A, 5)])
        assert results[0][1].startswith("error:")

    @pytest.mark.asyncio
    async def test_get_token_balance(self, sdk: ReputationSDK):
        balance = await sdk.get_token_balance(WALLET_A)
        assert balance == 1000.0

    def test_invalidate_cache(self, sdk: ReputationSDK):
        sdk._cache[WALLET_A] = OnChainReputation(wallet=WALLET_A, score=99)
        sdk.invalidate_cache(WALLET_A)
        assert WALLET_A not in sdk._cache

    def test_invalidate_cache_all(self, sdk: ReputationSDK):
        sdk._cache[WALLET_A] = OnChainReputation(wallet=WALLET_A)
        sdk._cache[WALLET_B] = OnChainReputation(wallet=WALLET_B)
        sdk.invalidate_cache()
        assert len(sdk._cache) == 0


# ---------------------------------------------------------------------------
# Integration service tests
# ---------------------------------------------------------------------------

class TestReputationIntegrationService:
    @pytest.mark.asyncio
    async def test_on_pr_merged_t1(self, service: ReputationIntegrationService):
        entry = await service.on_pr_merged(WALLET_A, BountyTier.T1, pr_url="https://github.com/pr/1")
        assert entry.delta == TIER_REPUTATION_REWARDS[BountyTier.T1]
        assert entry.reason == ReputationChangeReason.PR_MERGED
        score = service.get_score(WALLET_A)
        assert score.score == 1

    @pytest.mark.asyncio
    async def test_on_pr_merged_t2(self, service: ReputationIntegrationService):
        entry = await service.on_pr_merged(WALLET_A, BountyTier.T2)
        assert entry.delta == 5

    @pytest.mark.asyncio
    async def test_on_pr_merged_t3(self, service: ReputationIntegrationService):
        entry = await service.on_pr_merged(WALLET_A, BountyTier.T3)
        assert entry.delta == 20

    @pytest.mark.asyncio
    async def test_on_pr_merged_resets_rejection_counter(
        self, service: ReputationIntegrationService,
    ):
        # 2 rejections, then a merge should reset
        await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        await service.on_pr_merged(WALLET_A, BountyTier.T1)
        assert service._rejection_counts[WALLET_A] == 0

    @pytest.mark.asyncio
    async def test_on_pr_rejected_no_penalty_before_threshold(
        self, service: ReputationIntegrationService,
    ):
        result = await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        assert result is None  # no penalty yet

    @pytest.mark.asyncio
    async def test_on_pr_rejected_penalty_at_threshold(
        self, service: ReputationIntegrationService,
    ):
        # First give some reputation to lose
        await service.on_pr_merged(WALLET_A, BountyTier.T2)  # +5
        # 3 rejections
        await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        entry = await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        assert entry is not None
        assert entry.delta < 0
        assert entry.reason == ReputationChangeReason.PR_REJECTED

    @pytest.mark.asyncio
    async def test_cooldown_applied_after_penalty(
        self, service: ReputationIntegrationService,
    ):
        await service.on_pr_merged(WALLET_A, BountyTier.T1)
        for _ in range(REJECTION_THRESHOLD):
            await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        cooldowns = service._cooldowns.get(WALLET_A, [])
        assert len(cooldowns) == 1
        assert cooldowns[0].active is True
        assert cooldowns[0].bounty_tier == BountyTier.T1

    @pytest.mark.asyncio
    async def test_history_recorded(self, service: ReputationIntegrationService):
        await service.on_pr_merged(WALLET_A, BountyTier.T1)
        await service.on_pr_merged(WALLET_A, BountyTier.T2)
        items, total = service.get_history(WALLET_A)
        assert total == 2
        assert items[0].delta == 5  # newest first (T2)
        assert items[1].delta == 1  # older (T1)

    @pytest.mark.asyncio
    async def test_leaderboard(self, service: ReputationIntegrationService):
        await service.on_pr_merged(WALLET_A, BountyTier.T3)  # +20
        await service.on_pr_merged(WALLET_B, BountyTier.T1)  # +1
        scores, total = service.get_leaderboard()
        assert total == 2
        assert scores[0].wallet == WALLET_A
        assert scores[1].wallet == WALLET_B

    @pytest.mark.asyncio
    async def test_sync_wallet(self, service: ReputationIntegrationService):
        await service.on_pr_merged(WALLET_A, BountyTier.T1)
        score = await service.sync_wallet(WALLET_A)
        assert score.score == 1


# ---------------------------------------------------------------------------
# Eligibility tests
# ---------------------------------------------------------------------------

class TestEligibility:
    @pytest.mark.asyncio
    async def test_t1_eligible_by_default(self, service: ReputationIntegrationService):
        result = await service.check_eligibility(WALLET_A, BountyTier.T1)
        assert result.eligible is True
        assert result.meets_reputation is True
        assert result.meets_token_gate is True

    @pytest.mark.asyncio
    async def test_t2_requires_reputation(self, service: ReputationIntegrationService):
        result = await service.check_eligibility(WALLET_A, BountyTier.T2)
        # score=0 < 10 required
        assert result.meets_reputation is False
        assert result.eligible is False

    @pytest.mark.asyncio
    async def test_t2_eligible_with_reputation(
        self, service: ReputationIntegrationService,
    ):
        # Earn 10 reputation (2 T2 merges)
        await service.on_pr_merged(WALLET_A, BountyTier.T2)
        await service.on_pr_merged(WALLET_A, BountyTier.T2)
        result = await service.check_eligibility(WALLET_A, BountyTier.T2)
        assert result.meets_reputation is True
        assert result.eligible is True

    @pytest.mark.asyncio
    async def test_t2_requires_token_balance(self):
        client = MockSolanaClient(preset_balance=0.0)  # no tokens
        sdk = ReputationSDK(client=client)
        svc = ReputationIntegrationService(sdk)
        # Give enough reputation
        for _ in range(3):
            await svc.on_pr_merged(WALLET_A, BountyTier.T2)
        result = await svc.check_eligibility(WALLET_A, BountyTier.T2)
        assert result.meets_token_gate is False
        assert result.eligible is False

    @pytest.mark.asyncio
    async def test_cooldown_blocks_eligibility(
        self, service: ReputationIntegrationService,
    ):
        await service.on_pr_merged(WALLET_A, BountyTier.T1)
        for _ in range(REJECTION_THRESHOLD):
            await service.on_pr_rejected(WALLET_A, BountyTier.T1)
        result = await service.check_eligibility(WALLET_A, BountyTier.T1)
        assert result.cooldown_active is True
        assert result.eligible is False


# ---------------------------------------------------------------------------
# Tier classification tests
# ---------------------------------------------------------------------------

class TestReputationTier:
    def test_novice(self):
        assert ReputationTier.from_score(0) == ReputationTier.NOVICE
        assert ReputationTier.from_score(9) == ReputationTier.NOVICE

    def test_builder(self):
        assert ReputationTier.from_score(10) == ReputationTier.BUILDER
        assert ReputationTier.from_score(49) == ReputationTier.BUILDER

    def test_expert(self):
        assert ReputationTier.from_score(50) == ReputationTier.EXPERT
        assert ReputationTier.from_score(199) == ReputationTier.EXPERT

    def test_legend(self):
        assert ReputationTier.from_score(200) == ReputationTier.LEGEND
        assert ReputationTier.from_score(999) == ReputationTier.LEGEND


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

client = TestClient(app)


class TestReputationAPI:
    def test_get_reputation_no_service(self):
        """503 when service is not initialised."""
        from app.api import reputation as rep_api
        rep_api._service = None
        resp = client.get(f"/api/reputation/{WALLET_A}")
        assert resp.status_code == 503

    def test_get_reputation(self, api_service: ReputationIntegrationService):
        resp = client.get(f"/api/reputation/{WALLET_A}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["wallet"] == WALLET_A
        assert data["score"] == 0
        assert data["tier"] == "novice"

    def test_get_reputation_after_merge(self, api_service: ReputationIntegrationService):
        asyncio.get_event_loop().run_until_complete(
            api_service.on_pr_merged(WALLET_A, BountyTier.T1)
        )
        resp = client.get(f"/api/reputation/{WALLET_A}")
        assert resp.json()["score"] == 1

    def test_get_history_empty(self, api_service: ReputationIntegrationService):
        resp = client.get(f"/api/reputation/{WALLET_A}/history")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_history_with_data(self, api_service: ReputationIntegrationService):
        asyncio.get_event_loop().run_until_complete(
            api_service.on_pr_merged(WALLET_A, BountyTier.T2)
        )
        resp = client.get(f"/api/reputation/{WALLET_A}/history")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["delta"] == 5

    def test_eligibility_t1(self, api_service: ReputationIntegrationService):
        resp = client.get(f"/api/reputation/{WALLET_A}/eligibility?bounty_tier=1")
        assert resp.status_code == 200
        assert resp.json()["eligible"] is True

    def test_eligibility_t2_not_eligible(self, api_service: ReputationIntegrationService):
        resp = client.get(f"/api/reputation/{WALLET_A}/eligibility?bounty_tier=2")
        assert resp.status_code == 200
        assert resp.json()["eligible"] is False

    def test_eligibility_missing_tier(self, api_service: ReputationIntegrationService):
        resp = client.get(f"/api/reputation/{WALLET_A}/eligibility")
        assert resp.status_code == 422  # missing required param

    def test_leaderboard_empty(self, api_service: ReputationIntegrationService):
        resp = client.get("/api/reputation/leaderboard/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_leaderboard_with_data(self, api_service: ReputationIntegrationService):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(api_service.on_pr_merged(WALLET_A, BountyTier.T3))
        loop.run_until_complete(api_service.on_pr_merged(WALLET_B, BountyTier.T1))
        resp = client.get("/api/reputation/leaderboard/")
        data = resp.json()
        assert data["total"] == 2
        assert data["items"][0]["rank"] == 1
        assert data["items"][0]["wallet"] == WALLET_A

    def test_sync_specific_wallets(self, api_service: ReputationIntegrationService):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(api_service.on_pr_merged(WALLET_A, BountyTier.T1))
        resp = client.post("/api/reputation/sync", json={"wallets": [WALLET_A]})
        assert resp.status_code == 200
        assert resp.json()["synced"] == 1

    def test_sync_all(self, api_service: ReputationIntegrationService):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(api_service.on_pr_merged(WALLET_A, BountyTier.T1))
        loop.run_until_complete(api_service.on_pr_merged(WALLET_B, BountyTier.T1))
        resp = client.post("/api/reputation/sync", json={})
        assert resp.status_code == 200
        assert resp.json()["synced"] == 2
