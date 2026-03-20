"""Minimal in-memory bounty store shared across services."""

from app.models.bounty import BountyDB

# Canonical in-memory store: bounty_id -> BountyDB
_bounty_store: dict[str, BountyDB] = {}
