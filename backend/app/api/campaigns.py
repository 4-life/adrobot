from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_tracker
from app.api.schemas import CampaignOut, FetchOut, campaign_out
from app.campaigns.sync import fetch_all
from app.config import settings
from app.db import get_session
from app.models.campaign import Campaign, Stream
from app.tracker.port import TrackerProvider

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
Tracker = Annotated[TrackerProvider, Depends(get_tracker)]


@router.post("/sync/fetch")
async def fetch(session: Session, tracker: Tracker) -> FetchOut:
    result = await fetch_all(session, tracker)
    return FetchOut(
        fetched_at=result.fetched_at, campaigns=result.campaigns, conflicts=result.conflicts
    )


@router.get("/campaigns")
async def list_campaigns(
    session: Session, scope: Literal["ours", "all"] = "ours"
) -> list[CampaignOut]:
    """New drafts first, then the newest tracker campaigns. "ours": the name prefix."""
    query = (
        select(Campaign)
        .options(selectinload(Campaign.streams).selectinload(Stream.offers))
        .order_by(Campaign.external_id.desc().nulls_first())
    )
    if scope == "ours":
        ours = Campaign.name.startswith(settings.campaign_name_prefix, autoescape=True)
        query = query.where(ours)
    campaigns = await session.scalars(query)
    return [campaign_out(c) for c in campaigns]
