"""Campaigns as AdRobot keeps them: the tracker's synced state next to the local draft.

Vendor-neutral: `external_id` / `offer_id` are the tracker's ids, whichever tracker it is.
Model defaults apply only on insert; code that builds these objects sets every field it reads.
Forward references stay quoted: SQLAlchemy reads the annotations while each class is created.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ARCHIVED = "archived"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[int | None] = mapped_column(unique=True)  # null until pushed
    name: Mapped[str]
    alias: Mapped[str]
    domain_id: Mapped[int | None]
    domain_name: Mapped[str | None]
    group_id: Mapped[int | None]
    group_name: Mapped[str | None]
    traffic_source_id: Mapped[int | None]
    traffic_source_name: Mapped[str | None]
    state: Mapped[str] = mapped_column(default="active")  # active / disabled / archived
    # False: not the geo + offers layout; shown read-only.
    layout_supported: Mapped[bool] = mapped_column(default=True)
    conflict: Mapped[bool] = mapped_column(default=False)
    is_new: Mapped[bool] = mapped_column(default=False)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    streams: Mapped[list["Stream"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="Stream.position"
    )


class Stream(Base):
    __tablename__ = "streams"
    __table_args__ = (UniqueConstraint("campaign_id", "role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    external_id: Mapped[int | None] = mapped_column(unique=True)  # null until pushed
    role: Mapped[str]  # app.tracker.port GEO / OFFERS
    position: Mapped[int]
    # Geo stream only: the countries, as in the tracker and as they will be pushed.
    synced_geo: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    draft_geo: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    # The tracker's stream as last fetched or pushed; only the adapter reads it.
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    campaign: Mapped[Campaign] = relationship(back_populates="streams")
    offers: Mapped[list["StreamOffer"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan", order_by="StreamOffer.position"
    )


class StreamOffer(Base):
    __tablename__ = "stream_offers"
    __table_args__ = (UniqueConstraint("stream_id", "offer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"))
    offer_id: Mapped[int]  # the tracker's offer id
    name: Mapped[str]
    position: Mapped[int]  # list order: share rounding gives the extra points to the top ones
    synced_active: Mapped[bool]  # on the tracker's stream at the last fetch / push
    synced_share: Mapped[int | None]
    draft_active: Mapped[bool]  # False: listed under Removed
    draft_share: Mapped[int | None]
    pinned: Mapped[bool] = mapped_column(default=False)
    pinned_share: Mapped[int | None]
    removed_by: Mapped[str | None]  # "adrobot" / "tracker"
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    stream: Mapped[Stream] = relationship(back_populates="offers")


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"))
    action: Mapped[str]  # fetch / create / push
    step: Mapped[str | None]
    ok: Mapped[bool]
    error: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
