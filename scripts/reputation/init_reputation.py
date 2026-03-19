#!/usr/bin/env python3
"""Initialize the on-chain reputation program on Solana devnet.

Usage:
    python -m scripts.reputation.init_reputation --wallet <WALLET_ADDRESS>
    python -m scripts.reputation.init_reputation --wallet <WALLET_ADDRESS> --rpc https://api.devnet.solana.com

This creates the reputation PDA for the given wallet if it doesn't already
exist.  In a production deployment the ``SolanaClient`` implementation would
use ``solana-py`` to build and send real transactions; here we use a
lightweight devnet stub that logs what *would* happen.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Append project root so imports work when running as a script
sys.path.insert(0, ".")

from app.services.reputation_sdk import ReputationSDK, SolanaClient, derive_reputation_pda  # noqa: E402


# ---------------------------------------------------------------------------
# Devnet stub client
# ---------------------------------------------------------------------------

class DevnetStubClient:
    """Stub that simulates Solana devnet RPC calls."""

    def __init__(self, rpc_url: str = "https://api.devnet.solana.com") -> None:
        self.rpc_url = rpc_url
        self._accounts: dict[str, dict] = {}

    async def get_account_info(self, pubkey: str) -> Optional[dict]:
        logger.info("[devnet-stub] get_account_info(%s)", pubkey)
        return self._accounts.get(pubkey)

    async def send_transaction(self, tx_data: dict) -> str:
        instruction = tx_data.get("instruction", "unknown")
        logger.info("[devnet-stub] send_transaction — %s", instruction)
        # Simulate PDA creation
        if instruction == "initialize":
            pda = tx_data["accounts"]["reputation"]
            self._accounts[pda] = {"score": 0, "bump": 255}
        sig = f"devnet_sig_{instruction}_{id(tx_data)}"
        return sig

    async def get_token_balance(self, wallet: str, mint: str) -> float:
        logger.info("[devnet-stub] get_token_balance(%s, %s)", wallet, mint)
        return 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(wallet: str, rpc_url: str) -> None:
    client = DevnetStubClient(rpc_url)
    sdk = ReputationSDK(client=client)  # type: ignore[arg-type]

    pda = derive_reputation_pda(wallet)
    logger.info("Derived PDA: %s", pda)

    sig = await sdk.initialize_reputation(wallet)
    logger.info("Transaction signature: %s", sig)

    rep = await sdk.get_reputation(wallet)
    logger.info("On-chain reputation: score=%d initialized=%s", rep.score, rep.initialized)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize reputation PDA on devnet")
    parser.add_argument("--wallet", required=True, help="Solana wallet address (base-58)")
    parser.add_argument("--rpc", default="https://api.devnet.solana.com", help="Solana RPC URL")
    args = parser.parse_args()
    asyncio.run(main(args.wallet, args.rpc))
