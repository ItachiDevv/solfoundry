#!/usr/bin/env python3
"""Bulk-sync all contributor reputations between chain and platform DB.

Usage:
    python -m scripts.reputation.bulk_sync
    python -m scripts.reputation.bulk_sync --wallets wallet1,wallet2
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, ".")

from app.models.reputation import BountyTier  # noqa: E402
from app.services.reputation_integration import ReputationIntegrationService  # noqa: E402
from app.services.reputation_sdk import ReputationSDK  # noqa: E402


class DevnetSyncClient:
    """Stub Solana client for sync scripts."""

    def __init__(self) -> None:
        self._accounts: dict[str, dict] = {}
        self._counter = 0

    async def get_account_info(self, pubkey: str) -> Optional[dict]:
        return self._accounts.get(pubkey)

    async def send_transaction(self, tx_data: dict) -> str:
        self._counter += 1
        instruction = tx_data.get("instruction", "unknown")
        if instruction == "initialize":
            pda = tx_data["accounts"]["reputation"]
            self._accounts[pda] = {"score": 0, "bump": 255}
        elif instruction == "update_reputation":
            pda = tx_data["accounts"]["reputation"]
            if pda in self._accounts:
                delta = tx_data.get("data", {}).get("delta", 0)
                self._accounts[pda]["score"] = max(
                    0, self._accounts[pda].get("score", 0) + delta,
                )
        return f"sync_sig_{self._counter}"

    async def get_token_balance(self, wallet: str, mint: str) -> float:
        return 0.0


async def main(wallets: Optional[list[str]] = None) -> None:
    client = DevnetSyncClient()
    sdk = ReputationSDK(client=client)  # type: ignore[arg-type]
    service = ReputationIntegrationService(sdk)

    if wallets:
        # Seed wallets with a dummy merge so they exist in the store
        for w in wallets:
            await service.on_pr_merged(w, BountyTier.T1)
            logger.info("Seeded wallet %s", w)

    synced, errors = await service.sync_all()
    logger.info("Synced %d wallets", synced)
    if errors:
        for e in errors:
            logger.error("  Error: %s", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk-sync reputation scores")
    parser.add_argument("--wallets", default=None, help="Comma-separated wallet addresses")
    args = parser.parse_args()
    wallet_list = args.wallets.split(",") if args.wallets else None
    asyncio.run(main(wallet_list))
