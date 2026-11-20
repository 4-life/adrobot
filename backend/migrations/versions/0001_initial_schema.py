"""initial schema: campaigns, streams, stream offers, sync log

Revision ID: 0001
Revises:
Create Date: 2026-11-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("domain_id", sa.Integer(), nullable=True),
        sa.Column("domain_name", sa.String(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("group_name", sa.String(), nullable=True),
        sa.Column("traffic_source_id", sa.Integer(), nullable=True),
        sa.Column("traffic_source_name", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("layout_supported", sa.Boolean(), nullable=False),
        sa.Column("conflict", sa.Boolean(), nullable=False),
        sa.Column("is_new", sa.Boolean(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_campaigns_name", "campaigns", ["name"])

    op.create_table(
        "streams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("synced_geo", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("draft_geo", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("campaign_id", "role"),
    )

    op.create_table(
        "stream_offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "stream_id",
            sa.Integer(),
            sa.ForeignKey("streams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("synced_active", sa.Boolean(), nullable=False),
        sa.Column("synced_share", sa.Integer(), nullable=True),
        sa.Column("draft_active", sa.Boolean(), nullable=False),
        sa.Column("draft_share", sa.Integer(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("pinned_share", sa.Integer(), nullable=True),
        sa.Column("removed_by", sa.String(), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("stream_id", "offer_id"),
    )

    op.create_table(
        "sync_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("step", sa.String(), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sync_log")
    op.drop_table("stream_offers")
    op.drop_table("streams")
    op.drop_index("ix_campaigns_name", table_name="campaigns")
    op.drop_table("campaigns")
