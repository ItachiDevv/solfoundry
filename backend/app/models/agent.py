"""Agent registry database and Pydantic models."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AgentStatus(str, Enum):
    online = "online"
    offline = "offline"
    suspended = "suspended"


class AgentDB(Base):
    """SQLAlchemy model for the agents table."""

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    owner_wallet = Column(String(64), nullable=False, index=True)
    capabilities = Column(JSON, default=list, nullable=False)
    model = Column(String(100), nullable=False)
    endpoint_url = Column(String(500), nullable=False)
    status = Column(String(20), default=AgentStatus.offline.value, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)

    # Performance tracking
    bounties_attempted = Column(Integer, default=0, nullable=False)
    bounties_completed = Column(Integer, default=0, nullable=False)
    total_earnings = Column(Float, default=0.0, nullable=False)
    avg_review_score = Column(Float, default=0.0, nullable=False)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    owner_wallet: str = Field(
        ..., min_length=32, max_length=64, description="Solana wallet address"
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="e.g. ['code-review', 'bug-fix', 'audit']",
    )
    model: str = Field(..., max_length=100, description="LLM model powering agent")
    endpoint_url: str = Field(..., max_length=500, description="Agent callback URL")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    capabilities: Optional[list[str]] = None
    model: Optional[str] = Field(None, max_length=100)
    endpoint_url: Optional[str] = Field(None, max_length=500)


class AgentStats(BaseModel):
    bounties_attempted: int = 0
    bounties_completed: int = 0
    success_rate: float = 0.0
    total_earnings: float = 0.0
    avg_review_score: float = 0.0


class AgentResponse(BaseModel):
    id: str
    name: str
    owner_wallet: str
    capabilities: list[str]
    model: str
    endpoint_url: str
    status: AgentStatus
    last_heartbeat: Optional[datetime] = None
    stats: AgentStats
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListItem(BaseModel):
    id: str
    name: str
    owner_wallet: str
    capabilities: list[str]
    model: str
    status: AgentStatus
    stats: AgentStats

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentListItem]
    total: int
    skip: int
    limit: int


class HeartbeatResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    last_heartbeat: datetime
