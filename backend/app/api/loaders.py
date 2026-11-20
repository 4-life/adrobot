"""Loading campaigns for the routers: always with their streams and offers (async SQLAlchemy
can't lazy-load them later)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.campaigns import drafts
from app.campaigns.drafts import DraftError
from app.models.campaign import Campaign, Stream

WITH_STREAMS = selectinload(Campaign.streams).selectinload(Stream.offers)


async def load_campaign(session: AsyncSession, campaign_id: int) -> Campaign:
    campaign = await session.scalar(
        select(Campaign).where(Campaign.id == campaign_id).options(WITH_STREAMS)
    )
    if campaign is None:
        raise DraftError("not_found", f"Campaign {campaign_id} not found")
    return campaign


async def load_stream(session: AsyncSession, stream_id: int) -> Stream:
    """The stream with its whole campaign loaded, checked editable."""
    stream = await session.scalar(
        select(Stream)
        .where(Stream.id == stream_id)
        .options(selectinload(Stream.campaign).options(WITH_STREAMS))
    )
    if stream is None:
        raise DraftError("not_found", f"Stream {stream_id} not found")
    drafts.ensure_editable(stream.campaign)
    return stream
