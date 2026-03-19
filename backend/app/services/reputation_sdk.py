"""Python SDK to interact with the on-chain Reputation Anchor program.

All Solana interactions are abstracted behind ``SolanaClient`` so that tests
can inject a mock without touching the network.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Solana client protocol — production uses solana-py, tests use a mock
# ---------------------------------------------------------------------------

@runtime_checkable
class SolanaClient(Protocol):
    """Minimal interface required by the SDK."""

    async def get_account_info(self, pubkey: str) -> Optional[dict]:
        """Return account data dict or None if account doesn't exist."""
        ...

    async def send_transaction(self, tx_data: dict) -> str:
        """Build, sign, send a transaction. Return tx signature."""
        ...

    async def get_token_balance(self, wallet: str, mint: str) -> float:
        """SPL token balance for *wallet* of *mint*."""
        ...


# ---------------------------------------------------------------------------
# PDA helpers
# ---------------------------------------------------------------------------

REPUTATION_PROGRAM_ID = "RepPRGM1111111111111111111111111111111111111"
FNDRY_MINT = "FNDRYm1nt111111111111111111111111111111111111"


def derive_reputation_pda(wallet: str) -> str:
    """Deterministically derive the reputation PDA for a wallet.

    In production this would use ``Pubkey.find_program_address``.  For the SDK
    layer we replicate the seed logic so the address is predictable.
    """
    seed = f"reputation:{wallet}".encode()
    digest = hashlib.sha256(seed).hexdigest()[:32]
    return f"repPDA{digest}"


# ---------------------------------------------------------------------------
# On-chain reputation data
# ---------------------------------------------------------------------------

@dataclass
class OnChainReputation:
    wallet: str
    score: int = 0
    bump: int = 255
    initialized: bool = False


# ---------------------------------------------------------------------------
# Reputation SDK
# ---------------------------------------------------------------------------

@dataclass
class ReputationSDK:
    """High-level SDK for the on-chain reputation program."""

    client: SolanaClient
    program_id: str = REPUTATION_PROGRAM_ID
    fndry_mint: str = FNDRY_MINT
    payer_keypair: Optional[str] = None  # base-58 secret key (loaded from env)
    _cache: dict[str, OnChainReputation] = field(default_factory=dict)

    # -- initialise PDA ------------------------------------------------

    async def initialize_reputation(self, wallet: str) -> str:
        """Create the reputation PDA for a new contributor.

        Returns the transaction signature.
        """
        pda = derive_reputation_pda(wallet)
        existing = await self.client.get_account_info(pda)
        if existing is not None:
            logger.info("Reputation PDA already initialised for %s", wallet)
            return "already_initialized"

        tx_data = {
            "program_id": self.program_id,
            "instruction": "initialize",
            "accounts": {
                "reputation": pda,
                "contributor": wallet,
                "payer": self.payer_keypair or "DEFAULT_PAYER",
            },
            "data": {"wallet": wallet},
        }
        sig = await self.client.send_transaction(tx_data)
        self._cache[wallet] = OnChainReputation(wallet=wallet, score=0, initialized=True)
        logger.info("Initialized reputation PDA for %s — tx %s", wallet, sig)
        return sig

    # -- update reputation ---------------------------------------------

    async def update_reputation(self, wallet: str, delta: int) -> str:
        """Increment (or decrement) the reputation score on-chain.

        *delta* can be negative but the on-chain score is clamped at 0.
        Returns the transaction signature.
        """
        pda = derive_reputation_pda(wallet)
        tx_data = {
            "program_id": self.program_id,
            "instruction": "update_reputation",
            "accounts": {
                "reputation": pda,
                "authority": self.payer_keypair or "DEFAULT_PAYER",
            },
            "data": {"delta": delta},
        }
        sig = await self.client.send_transaction(tx_data)

        # Update local cache
        if wallet in self._cache:
            self._cache[wallet].score = max(0, self._cache[wallet].score + delta)
        else:
            score = await self._fetch_score(wallet)
            self._cache[wallet] = OnChainReputation(
                wallet=wallet, score=score, initialized=True,
            )

        logger.info("Updated reputation for %s by %+d — tx %s", wallet, delta, sig)
        return sig

    # -- query ---------------------------------------------------------

    async def get_reputation(self, wallet: str) -> OnChainReputation:
        """Read the current reputation from chain (or cache)."""
        if wallet in self._cache:
            return self._cache[wallet]

        pda = derive_reputation_pda(wallet)
        data = await self.client.get_account_info(pda)
        if data is None:
            return OnChainReputation(wallet=wallet, score=0, initialized=False)

        rep = OnChainReputation(
            wallet=wallet,
            score=data.get("score", 0),
            bump=data.get("bump", 255),
            initialized=True,
        )
        self._cache[wallet] = rep
        return rep

    async def get_token_balance(self, wallet: str) -> float:
        """Return the $FNDRY balance for *wallet*."""
        return await self.client.get_token_balance(wallet, self.fndry_mint)

    # -- batch ---------------------------------------------------------

    async def batch_update(
        self, updates: list[tuple[str, int]],
    ) -> list[tuple[str, str]]:
        """Apply multiple reputation updates.

        *updates* is a list of ``(wallet, delta)`` tuples.
        Returns ``[(wallet, tx_sig), ...]``.
        """
        results: list[tuple[str, str]] = []
        for wallet, delta in updates:
            try:
                sig = await self.update_reputation(wallet, delta)
                results.append((wallet, sig))
            except Exception as exc:  # noqa: BLE001
                logger.error("Batch update failed for %s: %s", wallet, exc)
                results.append((wallet, f"error:{exc}"))
        return results

    # -- internal helpers ----------------------------------------------

    async def _fetch_score(self, wallet: str) -> int:
        pda = derive_reputation_pda(wallet)
        data = await self.client.get_account_info(pda)
        if data is None:
            return 0
        return data.get("score", 0)

    def invalidate_cache(self, wallet: Optional[str] = None) -> None:
        """Drop cached data so next read hits the chain."""
        if wallet:
            self._cache.pop(wallet, None)
        else:
            self._cache.clear()
