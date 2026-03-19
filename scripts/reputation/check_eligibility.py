#!/usr/bin/env python3
"""CLI tool to check a wallet's eligibility for a specific bounty tier.

Usage:
    python -m scripts.reputation.check_eligibility --wallet <ADDR> --tier 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, ".")

from app.models.reputation import BountyTier  # noqa: E402
from app.services.reputation_integration import ReputationIntegrationService  # noqa: E402
from app.services.reputation_sdk import ReputationSDK  # noqa: E402


class StubClient:
    """Stub Solana client for eligibility checks."""

    def __init__(self, preset_score: int = 0, preset_balance: float = 0.0) -> None:
        self._score = preset_score
        self._balance = preset_balance
        self._accounts: dict[str, dict] = {}

    async def get_account_info(self, pubkey: str) -> Optional[dict]:
        return self._accounts.get(pubkey)

    async def send_transaction(self, tx_data: dict) -> str:
        instruction = tx_data.get("instruction", "unknown")
        if instruction == "initialize":
            pda = tx_data["accounts"]["reputation"]
            self._accounts[pda] = {"score": self._score, "bump": 255}
        return f"stub_sig_{id(tx_data)}"

    async def get_token_balance(self, wallet: str, mint: str) -> float:
        return self._balance


async def main(
    wallet: str,
    tier: int,
    preset_score: int,
    preset_balance: float,
) -> None:
    client = StubClient(preset_score=preset_score, preset_balance=preset_balance)
    sdk = ReputationSDK(client=client)  # type: ignore[arg-type]
    service = ReputationIntegrationService(sdk)

    # Seed the wallet so it has a score in the local store
    await sdk.initialize_reputation(wallet)

    bounty_tier = BountyTier(tier)
    result = await service.check_eligibility(wallet, bounty_tier)

    output = {
        "wallet": result.wallet,
        "bounty_tier": result.bounty_tier.value,
        "eligible": result.eligible,
        "reputation_score": result.reputation_score,
        "reputation_tier": result.reputation_tier.value,
        "meets_reputation": result.meets_reputation,
        "meets_token_gate": result.meets_token_gate,
        "cooldown_active": result.cooldown_active,
        "reasons": result.reasons,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check wallet bounty eligibility")
    parser.add_argument("--wallet", required=True, help="Solana wallet address")
    parser.add_argument("--tier", type=int, required=True, choices=[1, 2, 3], help="Bounty tier")
    parser.add_argument("--score", type=int, default=0, help="Preset reputation score (for testing)")
    parser.add_argument("--balance", type=float, default=0.0, help="Preset $FNDRY balance (for testing)")
    args = parser.parse_args()
    asyncio.run(main(args.wallet, args.tier, args.score, args.balance))
