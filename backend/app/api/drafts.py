"""Draft edits over HTTP. Nothing here calls the tracker except offer lookups for names."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tracker
from app.api.loaders import WITH_STREAMS, load_campaign, load_stream
from app.api.schemas import (
    AddOfferIn,
    CampaignOut,
    CancelAllOut,
    CancelOut,
    GeoIn,
    PinIn,
    campaign_out,
)
from app.campaigns import drafts
from app.campaigns.drafts import DraftError
from app.campaigns.pending import campaign_pending
from app.db import get_session
from app.models.campaign import Campaign, Stream
from app.tracker.cache import lookups
from app.tracker.port import TrackerProvider

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
Tracker = Annotated[TrackerProvider, Depends(get_tracker)]

async def saved(session: AsyncSession, stream: Stream) -> CampaignOut:
    await session.commit()
    return campaign_out(stream.campaign)


@router.put("/streams/{stream_id}/geo")
async def set_geo(stream_id: int, body: GeoIn, session: Session) -> CampaignOut:
    stream = await load_stream(session, stream_id)
    drafts.set_geo(stream, body.countries)
    return await saved(session, stream)


@router.post("/streams/{stream_id}/offers")
async def add_offer(
    stream_id: int, body: AddOfferIn, session: Session, tracker: Tracker
) -> CampaignOut:
    stream = await load_stream(session, stream_id)
    offers = await lookups.get("offers", tracker.list_offers)
    offer = next((o for o in offers if o.id == body.offer_id and o.active), None)
    if offer is None:
        raise DraftError("invalid", f"Offer {body.offer_id} isn't an active offer in the tracker")
    drafts.add_offer(stream, offer.id, offer.name)
    return await saved(session, stream)


@router.patch("/streams/{stream_id}/offers/{offer_id}")
async def set_pin(stream_id: int, offer_id: int, body: PinIn, session: Session) -> CampaignOut:
    stream = await load_stream(session, stream_id)
    drafts.set_pin(stream, offer_id, body.pinned, body.pinned_share)
    return await saved(session, stream)


@router.delete("/streams/{stream_id}/offers/{offer_id}")
async def remove_offer(stream_id: int, offer_id: int, session: Session) -> CampaignOut:
    stream = await load_stream(session, stream_id)
    drafts.remove_offer(stream, offer_id, datetime.now(UTC))
    return await saved(session, stream)


@router.post("/streams/{stream_id}/offers/{offer_id}/restore")
async def restore_offer(stream_id: int, offer_id: int, session: Session) -> CampaignOut:
    stream = await load_stream(session, stream_id)
    drafts.restore_offer(stream, offer_id)
    return await saved(session, stream)


@router.post("/campaigns/{campaign_id}/cancel")
async def cancel(campaign_id: int, session: Session) -> CancelOut:
    campaign = await load_campaign(session, campaign_id)
    if drafts.cancel(campaign):
        await session.delete(campaign)
        await session.commit()
        return CancelOut(deleted=True, campaign=None)
    await session.commit()
    return CancelOut(deleted=False, campaign=campaign_out(campaign))


@router.post("/sync/cancel-all")
async def cancel_all(session: Session) -> CancelAllOut:
    campaigns = await session.scalars(select(Campaign).options(WITH_STREAMS))
    cancelled = deleted = 0
    for campaign in campaigns:
        if not campaign_pending(campaign):
            continue
        if drafts.cancel(campaign):
            await session.delete(campaign)
            deleted += 1
        else:
            cancelled += 1
    await session.commit()
    return CancelAllOut(cancelled=cancelled, deleted=deleted)
