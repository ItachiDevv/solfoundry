"""In-memory agent service for MVP (mirrors contributor_service pattern)."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.agent import (
    AgentCreate,
    AgentDB,
    AgentListItem,
    AgentListResponse,
    AgentResponse,
    AgentStats,
    AgentStatus,
    AgentUpdate,
    HeartbeatResponse,
)

# In-memory store — will be replaced with a real DB later.
_store: dict[str, AgentDB] = {}

HEARTBEAT_TIMEOUT = timedelta(minutes=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_status(db: AgentDB) -> AgentStatus:
    """Derive live status from heartbeat timestamp."""
    if db.status == AgentStatus.suspended.value:
        return AgentStatus.suspended
    if db.last_heartbeat is None:
        return AgentStatus.offline
    cutoff = datetime.now(timezone.utc) - HEARTBEAT_TIMEOUT
    if db.last_heartbeat >= cutoff:
        return AgentStatus.online
    return AgentStatus.offline


def _success_rate(db: AgentDB) -> float:
    if db.bounties_attempted == 0:
        return 0.0
    return round(db.bounties_completed / db.bounties_attempted * 100, 2)


def _db_to_stats(db: AgentDB) -> AgentStats:
    return AgentStats(
        bounties_attempted=db.bounties_attempted,
        bounties_completed=db.bounties_completed,
        success_rate=_success_rate(db),
        total_earnings=db.total_earnings,
        avg_review_score=db.avg_review_score,
    )


def _db_to_response(db: AgentDB) -> AgentResponse:
    return AgentResponse(
        id=str(db.id),
        name=db.name,
        owner_wallet=db.owner_wallet,
        capabilities=db.capabilities or [],
        model=db.model,
        endpoint_url=db.endpoint_url,
        status=_compute_status(db),
        last_heartbeat=db.last_heartbeat,
        stats=_db_to_stats(db),
        created_at=db.created_at,
        updated_at=db.updated_at,
    )


def _db_to_list_item(db: AgentDB) -> AgentListItem:
    return AgentListItem(
        id=str(db.id),
        name=db.name,
        owner_wallet=db.owner_wallet,
        capabilities=db.capabilities or [],
        model=db.model,
        status=_compute_status(db),
        stats=_db_to_stats(db),
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_agent(data: AgentCreate) -> AgentResponse:
    now = datetime.now(timezone.utc)
    db = AgentDB(
        id=uuid.uuid4(),
        name=data.name,
        owner_wallet=data.owner_wallet,
        capabilities=data.capabilities,
        model=data.model,
        endpoint_url=data.endpoint_url,
        status=AgentStatus.offline.value,
        last_heartbeat=None,
        bounties_attempted=0,
        bounties_completed=0,
        total_earnings=0.0,
        avg_review_score=0.0,
        created_at=now,
        updated_at=now,
    )
    _store[str(db.id)] = db
    return _db_to_response(db)


def get_agent(agent_id: str) -> Optional[AgentResponse]:
    db = _store.get(agent_id)
    return _db_to_response(db) if db else None


def get_agent_by_name(name: str) -> Optional[AgentResponse]:
    for db in _store.values():
        if db.name == name:
            return _db_to_response(db)
    return None


def list_agents(
    role: Optional[str] = None,
    status: Optional[str] = None,
    min_success_rate: Optional[float] = None,
    skip: int = 0,
    limit: int = 20,
) -> AgentListResponse:
    results = list(_store.values())

    if role:
        results = [r for r in results if role in (r.capabilities or [])]

    if status:
        target = AgentStatus(status)
        results = [r for r in results if _compute_status(r) == target]

    if min_success_rate is not None:
        results = [r for r in results if _success_rate(r) >= min_success_rate]

    total = len(results)
    page = results[skip : skip + limit]
    return AgentListResponse(
        items=[_db_to_list_item(r) for r in page],
        total=total,
        skip=skip,
        limit=limit,
    )


def update_agent(
    agent_id: str, data: AgentUpdate
) -> Optional[AgentResponse]:
    db = _store.get(agent_id)
    if not db:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db, key, value)
    db.updated_at = datetime.now(timezone.utc)
    return _db_to_response(db)


def heartbeat(agent_id: str) -> Optional[HeartbeatResponse]:
    db = _store.get(agent_id)
    if not db:
        return None
    if db.status == AgentStatus.suspended.value:
        # Suspended agents cannot go online.
        return HeartbeatResponse(
            agent_id=str(db.id),
            status=AgentStatus.suspended,
            last_heartbeat=db.last_heartbeat or db.created_at,
        )
    now = datetime.now(timezone.utc)
    db.last_heartbeat = now
    db.status = AgentStatus.online.value
    db.updated_at = now
    return HeartbeatResponse(
        agent_id=str(db.id),
        status=AgentStatus.online,
        last_heartbeat=now,
    )
