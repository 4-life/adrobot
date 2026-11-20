from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_tracker
from app.api.schemas import (
    CampaignDefaultsOut,
    CampaignOut,
    CreateCampaignIn,
    FetchOut,
    campaign_out,
)
from app.campaigns.create import OfferPick, make_alias, new_draft, next_name, normalize_alias
from app.campaigns.drafts import DraftError
from app.campaigns.sync import fetch_all
from app.config import settings
from app.db import get_session
from app.models.campaign import Campaign, Stream
from app.tracker.cache import lookups
from app.tracker.port import LookupItem, TrackerProvider

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


async def _next_name(session: AsyncSession) -> str:
    prefix = settings.campaign_name_prefix
    names = await session.scalars(
        select(Campaign.name).where(Campaign.name.startswith(prefix, autoescape=True))
    )
    return next_name(prefix, names)


@router.get("/campaigns/defaults")
async def campaign_defaults(session: Session) -> CampaignDefaultsOut:
    name = await _next_name(session)
    return CampaignDefaultsOut(
        name=name,
        alias=make_alias(name),
        countries=[settings.default_geo],
        redirect_url=settings.geo_redirect_url,
    )


def _pick(items: list[LookupItem], item_id: int, what: str) -> LookupItem:
    found = next((i for i in items if i.id == item_id and i.active), None)
    if found is None:
        message = f"{what} {item_id} isn't an active {what.lower()} in the tracker"
        raise DraftError("invalid", message)
    return found


@router.post("/campaigns", status_code=201)
async def create_campaign(
    body: CreateCampaignIn, session: Session, tracker: Tracker
) -> CampaignOut:
    """A new draft campaign: shown as New, created in the tracker on Push."""
    name = body.name.strip() or await _next_name(session)
    alias = normalize_alias(body.alias) if body.alias.strip() else make_alias(name)
    if await session.scalar(select(Campaign.id).where(Campaign.alias == alias)) is not None:
        raise DraftError("conflict", f"Alias {alias!r} is already used by another campaign")

    domain = _pick(await lookups.get("domains", tracker.list_domains), body.domain_id, "Domain")
    group = None
    if body.group_id is not None:
        group = _pick(await lookups.get("groups", tracker.list_groups), body.group_id, "Group")
    source = None
    if body.traffic_source_id is not None:
        sources = await lookups.get("sources", tracker.list_sources)
        source = _pick(sources, body.traffic_source_id, "Source")
    offers = await lookups.get("offers", tracker.list_offers)
    picks = [OfferPick(o.id, o.name) for o in (_pick(offers, i, "Offer") for i in body.offer_ids)]

    campaign = new_draft(
        name=name,
        alias=alias,
        countries=body.countries or [settings.default_geo],
        domain_id=domain.id,
        domain_name=domain.name,
        group_id=group.id if group else None,
        group_name=group.name if group else None,
        traffic_source_id=source.id if source else None,
        traffic_source_name=source.name if source else None,
        offers=picks,
    )
    session.add(campaign)
    await session.commit()
    return campaign_out(campaign)
