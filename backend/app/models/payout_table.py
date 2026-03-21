"""SQLAlchemy ORM models for payouts and buyback records.

Provides persistent storage replacing in-memory dict stores.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class PayoutTable(Base):
    """Database model for payout records."""

    __tablename__ = "payouts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient = Column(String(100), nullable=False, index=True)
    recipient_wallet = Column(String(64), nullable=True)
    amount = Column(Float, nullable=False)
    token = Column(String(20), nullable=False, default="FNDRY")
    bounty_id = Column(String(100), nullable=True)
    bounty_title = Column(String(200), nullable=True)
    tx_hash = Column(String(128), nullable=True, unique=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    solscan_url = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))


class BuybackTable(Base):
    """Database model for buyback event records."""

    __tablename__ = "buybacks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount_sol = Column(Float, nullable=False)
    amount_fndry = Column(Float, nullable=False)
    price_per_fndry = Column(Float, nullable=False)
    tx_hash = Column(String(128), nullable=True, unique=True, index=True)
    solscan_url = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
