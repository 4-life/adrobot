"""Push to the tracker, and conflict resolution."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tracker
from app.api.drafts import WITH_STREAMS, load_campaign
from app.api.schemas import (
    CancelOut,
    PushAllOut,
    PushItemOut,
    PushOut,
    ResolveIn,
    campaign_out,
)
from app.campaigns import drafts
from app.campaigns.drafts import DraftError
from app.campaigns.pending import campaign_pending
from app.campaigns.push import push
from app.config import settings
from app.db import get_session
from app.models.campaign import Campaign
from app.tracker.port import TrackerError, TrackerProvider

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
Tracker = Annotated[TrackerProvider, Depends(get_tracker)]


@router.post("/campaigns/{campaign_id}/push")
async def push_campaign(campaign_id: int, session: Session, tracker: Tracker) -> PushOut:
    campaign = await load_campaign(session, campaign_id)
    result = await push(session, tracker, campaign, settings.geo_redirect_url)
    await session.commit()
    return PushOut(pushed=result.pushed, mismatch=result.mismatch, campaign=campaign_out(campaign))


@router.post("/sync/push-all")
async def push_all(session: Session, tracker: Tracker) -> PushAllOut:
    """Every pending campaign, one by one: a failure is reported and the rest go on."""
    campaigns = await session.scalars(select(Campaign).options(WITH_STREAMS))
    results: list[PushItemOut] = []
    for campaign in [c for c in campaigns if campaign_pending(c)]:
        try:
            result = await push(session, tracker, campaign, settings.geo_redirect_url)
        except (DraftError, TrackerError) as error:
            item = PushItemOut(
                campaign_id=campaign.id,
                name=campaign.name,
                ok=False,
                error=error.message,
                mismatch=[],
            )
        else:
            item = PushItemOut(
                campaign_id=campaign.id,
                name=campaign.name,
                ok=True,
                error=None,
                mismatch=result.mismatch,
            )
        results.append(item)
    await session.commit()
    return PushAllOut(results=results)


@router.post("/campaigns/{campaign_id}/resolve")
async def resolve(campaign_id: int, body: ResolveIn, session: Session) -> CancelOut:
    """Keep the draft (the next push goes over the tracker's version) or cancel it."""
    campaign = await load_campaign(session, campaign_id)
    if not campaign.conflict:
        raise DraftError("conflict", "The campaign has no conflict to resolve")
    if body.keep_draft:
        campaign.conflict = False
        await session.commit()
        return CancelOut(deleted=False, campaign=campaign_out(campaign))
    if drafts.cancel(campaign):
        await session.delete(campaign)
        await session.commit()
        return CancelOut(deleted=True, campaign=None)
    await session.commit()
    return CancelOut(deleted=False, campaign=campaign_out(campaign))
