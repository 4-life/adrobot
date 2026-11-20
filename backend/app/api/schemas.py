from datetime import datetime

from pydantic import BaseModel

from app.campaigns.drafts import share_errors
from app.campaigns.pending import (
    OfferChange,
    campaign_pending,
    geo_changes,
    offer_change,
    stream_pending,
)
from app.models.campaign import ARCHIVED, Campaign, Stream, StreamOffer


class OfferOut(BaseModel):
    id: int
    offer_id: int
    name: str
    position: int
    synced_active: bool
    synced_share: int | None
    draft_active: bool
    draft_share: int | None
    pinned: bool
    pinned_share: int | None
    removed_by: str | None
    removed_at: datetime | None
    change: OfferChange | None  # vs. synced: added / removed / share
    pending: bool


class StreamOut(BaseModel):
    id: int
    external_id: int | None
    role: str
    position: int
    synced_geo: list[str] | None
    draft_geo: list[str] | None
    geo_added: list[str]
    geo_removed: list[str]
    offers: list[OfferOut]
    errors: list[str]  # why the draft can't be pushed
    pending: bool


class CampaignOut(BaseModel):
    id: int
    external_id: int | None
    name: str
    alias: str
    domain_id: int | None
    domain_name: str | None
    group_id: int | None
    group_name: str | None
    traffic_source_id: int | None
    traffic_source_name: str | None
    state: str
    archived: bool
    layout_supported: bool
    conflict: bool
    is_new: bool
    pending: bool
    fetched_at: datetime | None
    streams: list[StreamOut]


class FetchOut(BaseModel):
    fetched_at: datetime
    campaigns: int
    conflicts: list[int]


class LookupOut(BaseModel):
    id: int
    name: str


class CancelOut(BaseModel):
    deleted: bool  # a new draft campaign was dropped entirely
    campaign: CampaignOut | None


class CancelAllOut(BaseModel):
    cancelled: int
    deleted: int


class GeoIn(BaseModel):
    countries: list[str]


class AddOfferIn(BaseModel):
    offer_id: int


class PinIn(BaseModel):
    pinned: bool
    pinned_share: int | None = None


class CampaignDefaultsOut(BaseModel):
    """Prefills the New campaign form."""

    name: str
    alias: str
    countries: list[str]
    redirect_url: str


class CreateCampaignIn(BaseModel):
    name: str = ""  # blank: the next CAMPAIGN_NAME_PREFIX + N
    alias: str = ""  # blank: generated from the name
    countries: list[str] = []  # empty: DEFAULT_GEO
    domain_id: int
    group_id: int | None = None
    traffic_source_id: int | None = None
    offer_ids: list[int]


def offer_out(offer: StreamOffer) -> OfferOut:
    return OfferOut(
        id=offer.id,
        offer_id=offer.offer_id,
        name=offer.name,
        position=offer.position,
        synced_active=offer.synced_active,
        synced_share=offer.synced_share,
        draft_active=offer.draft_active,
        draft_share=offer.draft_share,
        pinned=offer.pinned,
        pinned_share=offer.pinned_share,
        removed_by=offer.removed_by,
        removed_at=offer.removed_at,
        change=offer_change(offer),
        pending=offer_change(offer) is not None,
    )


def stream_out(stream: Stream) -> StreamOut:
    added, removed = geo_changes(stream)
    return StreamOut(
        id=stream.id,
        external_id=stream.external_id,
        role=stream.role,
        position=stream.position,
        synced_geo=stream.synced_geo,
        draft_geo=stream.draft_geo,
        geo_added=added,
        geo_removed=removed,
        offers=[offer_out(o) for o in stream.offers],
        errors=share_errors(stream),
        pending=stream_pending(stream),
    )


def campaign_out(campaign: Campaign) -> CampaignOut:
    return CampaignOut(
        id=campaign.id,
        external_id=campaign.external_id,
        name=campaign.name,
        alias=campaign.alias,
        domain_id=campaign.domain_id,
        domain_name=campaign.domain_name,
        group_id=campaign.group_id,
        group_name=campaign.group_name,
        traffic_source_id=campaign.traffic_source_id,
        traffic_source_name=campaign.traffic_source_name,
        state=campaign.state,
        archived=campaign.state == ARCHIVED,
        layout_supported=campaign.layout_supported,
        conflict=campaign.conflict,
        is_new=campaign.is_new,
        pending=campaign_pending(campaign),
        fetched_at=campaign.fetched_at,
        streams=[stream_out(s) for s in campaign.streams],
    )


class PushOut(BaseModel):
    pushed: bool  # False: nothing was pending
    mismatch: list[str]  # where the tracker stored something other than what was sent
    campaign: CampaignOut


class PushItemOut(BaseModel):
    campaign_id: int
    name: str
    ok: bool
    error: str | None
    mismatch: list[str]


class PushAllOut(BaseModel):
    results: list[PushItemOut]


class ResolveIn(BaseModel):
    keep_draft: bool  # True: push the draft over the tracker's version; False: cancel it
