"""Create contributors table. Revision 002."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = None


def upgrade() -> None:
    op.create_table("contributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255)), sa.Column("avatar_url", sa.String(500)),
        sa.Column("bio", sa.Text()), sa.Column("skills", sa.JSON(), server_default="[]"),
        sa.Column("badges", sa.JSON(), server_default="[]"),
        sa.Column("social_links", sa.JSON(), server_default="{}"),
        sa.Column("total_contributions", sa.Integer(), server_default="0"),
        sa.Column("total_bounties_completed", sa.Integer(), server_default="0"),
        sa.Column("total_earnings", sa.Float(), server_default="0.0"),
        sa.Column("reputation_score", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("contributors")
