"""Create agents table.

Revision ID: 001
Revises: None
Create Date: 2026-03-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("owner_wallet", sa.String(64), nullable=False, index=True),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("endpoint_url", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="offline",
        ),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "bounties_attempted", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "bounties_completed", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_earnings", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "avg_review_score", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("agents")
