"""Contributor service -- async PostgreSQL with in-memory fallback.

PostgreSQL migration path: table ``contributors`` is created by
``init_db()`` via ``app.database.Base``.  Alembic migration at
``migrations/versions/002_create_contributors_table.py``.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contributor import (
    ContributorDB,
    ContributorCreate,
    ContributorListItem,
    ContributorListResponse,
    ContributorResponse,
    ContributorStats,
    ContributorUpdate,
)

logger = logging.getLogger(__name__)

_store: dict[str, ContributorDB] = {}


def _db_to_response(db: ContributorDB) -> ContributorResponse:
    """Convert a ContributorDB record to an API response model."""
    now = datetime.now(timezone.utc)
    return ContributorResponse(
        id=str(db.id),
        username=db.username,
        display_name=db.display_name,
        email=db.email,
        avatar_url=db.avatar_url,
        bio=db.bio,
        skills=db.skills or [],
        badges=db.badges or [],
        social_links=db.social_links or {},
        stats=ContributorStats(
            total_contributions=db.total_contributions or 0,
            total_bounties_completed=db.total_bounties_completed or 0,
            total_earnings=db.total_earnings or 0.0,
            reputation_score=db.reputation_score or 0,
        ),
        created_at=db.created_at or now,
        updated_at=db.updated_at or now,
    )


def _db_to_list_item(db: ContributorDB) -> ContributorListItem:
    """Convert a ContributorDB record to a list-item summary."""
    return ContributorListItem(
        id=str(db.id),
        username=db.username,
        display_name=db.display_name,
        avatar_url=db.avatar_url,
        skills=db.skills or [],
        badges=db.badges or [],
        stats=ContributorStats(
            total_contributions=db.total_contributions or 0,
            total_bounties_completed=db.total_bounties_completed or 0,
            total_earnings=db.total_earnings or 0.0,
            reputation_score=db.reputation_score or 0,
        ),
    )


def create_contributor(data: ContributorCreate) -> ContributorResponse:
    """Create a contributor in the in-memory store."""
    now = datetime.now(timezone.utc)
    db = ContributorDB(
        id=uuid.uuid4(),
        username=data.username,
        display_name=data.display_name,
        email=data.email,
        avatar_url=data.avatar_url,
        bio=data.bio,
        skills=data.skills,
        badges=data.badges,
        social_links=data.social_links,
        total_contributions=0,
        total_bounties_completed=0,
        total_earnings=0.0,
        reputation_score=0,
        created_at=now,
        updated_at=now,
    )
    _store[str(db.id)] = db
    return _db_to_response(db)


def list_contributors(
    search: Optional[str] = None,
    skills: Optional[list[str]] = None,
    badges: Optional[list[str]] = None,
    skip: int = 0,
    limit: int = 20,
) -> ContributorListResponse:
    results = list(_store.values())
    if search:
        q = search.lower()
        results = [
            r for r in results if q in r.username.lower() or q in r.display_name.lower()
        ]
    if skills:
        s = set(skills)
        results = [r for r in results if s & set(r.skills or [])]
    if badges:
        b = set(badges)
        results = [r for r in results if b & set(r.badges or [])]
    total = len(results)
    return ContributorListResponse(
        items=[_db_to_list_item(r) for r in results[skip : skip + limit]],
        total=total,
        skip=skip,
        limit=limit,
    )


def get_contributor(contributor_id: str) -> Optional[ContributorResponse]:
    db = _store.get(contributor_id)
    return _db_to_response(db) if db else None


def get_contributor_by_username(username: str) -> Optional[ContributorResponse]:
    for db in _store.values():
        if db.username == username:
            return _db_to_response(db)
    return None


def update_contributor(
    contributor_id: str, data: ContributorUpdate
) -> Optional[ContributorResponse]:
    db = _store.get(contributor_id)
    if not db:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db, key, value)
    db.updated_at = datetime.now(timezone.utc)
    return _db_to_response(db)


def delete_contributor(contributor_id: str) -> bool:
    """Delete a contributor from the in-memory store."""
    return _store.pop(contributor_id, None) is not None


# ---------------------------------------------------------------------------
# Async PostgreSQL operations — mirror writes for cross-restart persistence
# ---------------------------------------------------------------------------


async def create_contributor_async(
    data: ContributorCreate, session: AsyncSession
) -> ContributorResponse:
    """Persist a new contributor to PostgreSQL."""
    now = datetime.now(timezone.utc)
    db = ContributorDB(
        id=uuid.uuid4(), username=data.username, display_name=data.display_name,
        email=data.email, avatar_url=data.avatar_url, bio=data.bio,
        skills=data.skills, badges=data.badges, social_links=data.social_links,
        total_contributions=0, total_bounties_completed=0,
        total_earnings=0.0, reputation_score=0, created_at=now, updated_at=now,
    )
    session.add(db)
    await session.commit()
    await session.refresh(db)
    _store[str(db.id)] = db
    return _db_to_response(db)


async def update_contributor_async(
    contributor_id: str, data: ContributorUpdate, session: AsyncSession
) -> Optional[ContributorResponse]:
    """Update a contributor in PostgreSQL."""
    try:
        uid = uuid.UUID(contributor_id)
    except ValueError:
        return None
    db = (await session.execute(
        select(ContributorDB).where(ContributorDB.id == uid)
    )).scalar_one_or_none()
    if not db:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db, key, value)
    db.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(db)
    _store[str(db.id)] = db
    return _db_to_response(db)


async def delete_contributor_async(
    contributor_id: str, session: AsyncSession
) -> bool:
    """Delete a contributor from PostgreSQL."""
    try:
        uid = uuid.UUID(contributor_id)
    except ValueError:
        return False
    db = (await session.execute(
        select(ContributorDB).where(ContributorDB.id == uid)
    )).scalar_one_or_none()
    if not db:
        return False
    await session.delete(db)
    await session.commit()
    _store.pop(contributor_id, None)
    return True
