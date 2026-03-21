"""PostgreSQL persistence: load from DB on startup, persist writes to DB."""

import logging
from datetime import datetime, timezone
from sqlalchemy import select, delete
from app.database import get_db_session

logger = logging.getLogger(__name__)


async def load_bounties_from_database() -> int:
    """Load bounties from DB into in-memory store."""
    from app.models.bounty_table import BountyTable
    from app.models.bounty import BountyDB, BountyStatus, BountyTier
    from app.services.bounty_service import _bounty_store
    try:
        async with get_db_session() as session:
            rows = (await session.execute(select(BountyTable))).scalars().all()
            for row in rows:
                bid = str(row.id)
                _bounty_store[bid] = BountyDB(
                    id=bid, title=row.title, description=row.description or "",
                    tier=BountyTier(row.tier), reward_amount=row.reward_amount,
                    status=BountyStatus(row.status), github_issue_url=row.github_issue_url,
                    required_skills=row.skills if isinstance(row.skills, list) else [],
                    deadline=row.deadline, created_by=row.created_by or "system",
                    created_at=row.created_at or datetime.now(timezone.utc),
                    updated_at=row.updated_at or datetime.now(timezone.utc))
            return len(rows)
    except Exception as error:
        logger.warning("Failed to load bounties: %s", error)
        return 0


async def load_contributors_from_database() -> int:
    """Load contributors from DB into in-memory store."""
    from app.models.contributor import ContributorDB
    from app.services.contributor_service import _store
    try:
        async with get_db_session() as session:
            rows = (await session.execute(select(ContributorDB))).scalars().all()
            for row in rows:
                _store[str(row.id)] = row
            return len(rows)
    except Exception as error:
        logger.warning("Failed to load contributors: %s", error)
        return 0


async def load_payouts_from_database() -> int:
    """Load payouts and buybacks from DB into in-memory stores."""
    from app.models.payout_table import PayoutTable, BuybackTable
    from app.models.payout import PayoutRecord, PayoutStatus, BuybackRecord
    from app.services.payout_service import _payout_store, _buyback_store
    try:
        async with get_db_session() as session:
            for row in (await session.execute(select(PayoutTable))).scalars().all():
                rec = PayoutRecord(
                    id=str(row.id), recipient=row.recipient,
                    recipient_wallet=row.recipient_wallet, amount=row.amount,
                    token=row.token, bounty_id=row.bounty_id,
                    bounty_title=row.bounty_title, tx_hash=row.tx_hash,
                    status=PayoutStatus(row.status), solscan_url=row.solscan_url,
                    created_at=row.created_at or datetime.now(timezone.utc))
                _payout_store[rec.id] = rec
            for row in (await session.execute(select(BuybackTable))).scalars().all():
                rec = BuybackRecord(
                    id=str(row.id), amount_sol=row.amount_sol,
                    amount_fndry=row.amount_fndry, price_per_fndry=row.price_per_fndry,
                    tx_hash=row.tx_hash, solscan_url=row.solscan_url,
                    created_at=row.created_at or datetime.now(timezone.utc))
                _buyback_store[rec.id] = rec
            return len(_payout_store)
    except Exception as error:
        logger.warning("Failed to load payouts: %s", error)
        return 0


async def persist_payout(payout_id: str) -> bool:
    """Persist a payout to the database."""
    from app.models.payout_table import PayoutTable
    from app.services.payout_service import _payout_store
    rec = _payout_store.get(payout_id)
    if not rec:
        return False
    try:
        async with get_db_session() as session:
            session.add(PayoutTable(
                id=rec.id, recipient=rec.recipient, recipient_wallet=rec.recipient_wallet,
                amount=rec.amount, token=rec.token, bounty_id=rec.bounty_id,
                bounty_title=rec.bounty_title, tx_hash=rec.tx_hash,
                status=rec.status.value, solscan_url=rec.solscan_url,
                created_at=rec.created_at))
            await session.commit()
            return True
    except Exception as error:
        logger.warning("Failed to persist payout %s: %s", payout_id, error)
        return False


async def persist_buyback(buyback_id: str) -> bool:
    """Persist a buyback to the database."""
    from app.models.payout_table import BuybackTable
    from app.services.payout_service import _buyback_store
    rec = _buyback_store.get(buyback_id)
    if not rec:
        return False
    try:
        async with get_db_session() as session:
            session.add(BuybackTable(
                id=rec.id, amount_sol=rec.amount_sol, amount_fndry=rec.amount_fndry,
                price_per_fndry=rec.price_per_fndry, tx_hash=rec.tx_hash,
                solscan_url=rec.solscan_url, created_at=rec.created_at))
            await session.commit()
            return True
    except Exception as error:
        logger.warning("Failed to persist buyback %s: %s", buyback_id, error)
        return False


async def persist_contributor(contributor_id: str) -> bool:
    """Persist a contributor via merge (insert or update)."""
    from app.services.contributor_service import _store
    rec = _store.get(contributor_id)
    if not rec:
        return False
    try:
        async with get_db_session() as session:
            await session.merge(rec)
            await session.commit()
            return True
    except Exception as error:
        logger.warning("Failed to persist contributor %s: %s", contributor_id, error)
        return False


async def delete_contributor_from_database(contributor_id: str) -> bool:
    """Remove a contributor from the database."""
    from app.models.contributor import ContributorDB
    try:
        async with get_db_session() as session:
            await session.execute(
                delete(ContributorDB).where(ContributorDB.id == contributor_id))
            await session.commit()
            return True
    except Exception as error:
        logger.warning("Failed to delete contributor %s: %s", contributor_id, error)
        return False


async def load_all_from_database() -> dict[str, int]:
    """Load all data from database into in-memory stores on startup."""
    return {
        "bounties": await load_bounties_from_database(),
        "contributors": await load_contributors_from_database(),
        "payouts": await load_payouts_from_database(),
    }
