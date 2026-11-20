"""Push to the tracker: a new campaign is created step by step, an existing one gets its
changed streams. Depends only on the tracker port.

- A new campaign: campaign → geo stream → offers stream. Each tracker id is committed as soon
  as it comes back, so a push that fails partway resumes from the failed step.
- An existing campaign: the tracker is re-read first. If it changed since the last fetch, the
  push is refused and the campaign is flagged Conflict (the synced state is updated).
- Afterwards the campaign is re-read: synced and draft become what the tracker stored, and any
  difference from what was sent is reported (`mismatch`).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.campaigns.drafts import DraftError, active_offers, ensure_editable, share_errors
from app.campaigns.merge import merge_streams
from app.campaigns.pending import campaign_pending, stream_pending
from app.models.campaign import Campaign, Stream, SyncLog
from app.tracker.port import (
    GEO,
    OFFERS,
    NewCampaign,
    NewGeoStream,
    NewOffersStream,
    OfferShare,
    TrackerError,
    TrackerProvider,
    TrackerStream,
)


class Store(Protocol):
    """What push needs from the database session (an AsyncSession in the app)."""

    def add(self, instance: object) -> None: ...

    async def commit(self) -> None: ...


@dataclass(frozen=True)
class PushResult:
    pushed: bool  # False: nothing was pending
    mismatch: list[str]  # where the tracker stored something other than what was sent


def stream_of(campaign: Campaign, role: str) -> Stream:
    return next(s for s in campaign.streams if s.role == role)


def check_pushable(campaign: Campaign) -> None:
    ensure_editable(campaign)
    if campaign.conflict:
        raise DraftError(
            "conflict", "The tracker changed under this draft: keep the draft or cancel it first"
        )
    errors = share_errors(stream_of(campaign, OFFERS))
    if errors:
        raise DraftError("invalid", "; ".join(errors))
    if not stream_of(campaign, GEO).draft_geo:
        raise DraftError("invalid", "The geo stream needs at least one country")


def draft_offers(campaign: Campaign) -> list[OfferShare]:
    active = active_offers(stream_of(campaign, OFFERS))
    return [OfferShare(o.offer_id, o.draft_share or 0) for o in active]


def tracker_matches_synced(campaign: Campaign, current: list[TrackerStream]) -> bool:
    by_role = {s.role: s for s in current}
    geo, offers = stream_of(campaign, GEO), stream_of(campaign, OFFERS)
    synced_offers = {(o.offer_id, o.synced_share) for o in offers.offers if o.synced_active}
    current_offers = {(o.offer_id, o.share) for o in by_role[OFFERS].offers}
    return by_role[GEO].geo == geo.synced_geo and current_offers == synced_offers


def differences(
    sent_geo: list[str], sent: list[OfferShare], stored: list[TrackerStream]
) -> list[str]:
    by_role = {s.role: s for s in stored}
    found: list[str] = []
    if by_role[GEO].geo != sent_geo:
        found.append(f"Geo: sent {sent_geo}, the tracker has {by_role[GEO].geo}")
    sent_offers = {(o.offer_id, o.share) for o in sent}
    stored_offers = {(o.offer_id, o.share) for o in by_role[OFFERS].offers}
    if stored_offers != sent_offers:
        found.append(f"Offers: sent {sorted(sent_offers)}, the tracker has {sorted(stored_offers)}")
    return found


def mark_sent(campaign: Campaign) -> None:
    """The draft becomes the synced baseline, before the re-read corrects it to the truth."""
    geo = stream_of(campaign, GEO)
    geo.synced_geo = list(geo.draft_geo or [])
    for offer in stream_of(campaign, OFFERS).offers:
        offer.synced_active = offer.draft_active
        offer.synced_share = offer.draft_share if offer.draft_active else None


async def _log(store: Store, campaign: Campaign, step: str, error: str | None = None) -> None:
    store.add(
        SyncLog(campaign_id=campaign.id, action="push", step=step, ok=error is None, error=error)
    )
    await store.commit()


def _campaign_id(campaign: Campaign) -> int:
    if campaign.external_id is None:
        raise AssertionError("the campaign has no tracker id yet")
    return campaign.external_id


async def _create(
    store: Store, tracker: TrackerProvider, campaign: Campaign, redirect: str
) -> None:
    if campaign.external_id is None:
        if campaign.domain_id is None:
            raise DraftError("invalid", "A new campaign needs a domain")
        campaign.external_id = await tracker.create_campaign(
            NewCampaign(
                name=campaign.name,
                alias=campaign.alias,
                domain_id=campaign.domain_id,
                group_id=campaign.group_id,
                traffic_source_id=campaign.traffic_source_id,
            )
        )
        await _log(store, campaign, "create campaign")
    geo = stream_of(campaign, GEO)
    if geo.external_id is None:
        geo.external_id = await tracker.create_geo_stream(
            NewGeoStream(_campaign_id(campaign), list(geo.draft_geo or []), redirect)
        )
        await _log(store, campaign, "create geo stream")
    offers = stream_of(campaign, OFFERS)
    if offers.external_id is None:
        offers.external_id = await tracker.create_offers_stream(
            NewOffersStream(_campaign_id(campaign), draft_offers(campaign))
        )
        await _log(store, campaign, "create offers stream")


async def _update(
    store: Store, tracker: TrackerProvider, campaign: Campaign, now: datetime
) -> None:
    current = await tracker.get_streams(_campaign_id(campaign))
    if current is None:
        campaign.layout_supported = False
        await store.commit()
        raise DraftError("conflict", "The campaign is no longer geo + offers in the tracker")
    if not tracker_matches_synced(campaign, current):
        merge_streams(campaign, current, now)
        campaign.conflict = True
        await _log(store, campaign, "conflict check", "the tracker changed since the last fetch")
        raise DraftError(
            "conflict", "The tracker changed since the last fetch: keep the draft or cancel it"
        )
    by_role = {s.role: s for s in current}
    if stream_pending(stream_of(campaign, GEO)):
        await tracker.push_geo(by_role[GEO], list(stream_of(campaign, GEO).draft_geo or []))
        await _log(store, campaign, "push geo")
    if stream_pending(stream_of(campaign, OFFERS)):
        await tracker.push_offers(by_role[OFFERS], draft_offers(campaign))
        await _log(store, campaign, "push offers")


async def push(
    store: Store,
    tracker: TrackerProvider,
    campaign: Campaign,
    redirect_url: str,
    now: datetime | None = None,
) -> PushResult:
    now = now or datetime.now(UTC)
    check_pushable(campaign)
    if not campaign_pending(campaign):
        return PushResult(pushed=False, mismatch=[])

    sent_geo = list(stream_of(campaign, GEO).draft_geo or [])
    sent_offers = draft_offers(campaign)
    try:
        if campaign.is_new:
            await _create(store, tracker, campaign, redirect_url)
        else:
            await _update(store, tracker, campaign, now)
        stored = await tracker.get_streams(_campaign_id(campaign))
    except TrackerError as error:
        await _log(store, campaign, "push", error.message)
        raise

    mark_sent(campaign)
    campaign.is_new = False
    campaign.fetched_at = now
    if stored is None:
        campaign.layout_supported = False
        mismatch = ["The tracker's streams aren't geo + offers after the push"]
    else:
        mismatch = differences(sent_geo, sent_offers, stored)
        merge_streams(campaign, stored, now)
    await _log(store, campaign, "done", "; ".join(mismatch) or None)
    return PushResult(pushed=True, mismatch=mismatch)
