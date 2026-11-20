"""Merges a tracker fetch into AdRobot's campaigns. No IO: works on ORM objects in memory.

The synced state always becomes what the tracker has. A stream without pending changes gets
its draft reset to it; a stream with pending changes keeps its draft, and the campaign is
flagged Conflict when the tracker changed under it. Knows only the tracker port's types.
"""

from datetime import datetime

from app.campaigns.pending import campaign_pending, offer_pending
from app.models.campaign import Campaign, Stream, StreamOffer
from app.tracker.port import GEO, TrackerCampaign, TrackerOffer, TrackerStream

REMOVED_BY_TRACKER = "tracker"


def apply_campaign_fields(campaign: Campaign, tracked: TrackerCampaign, now: datetime) -> None:
    campaign.external_id = tracked.external_id
    campaign.name = tracked.name
    campaign.alias = tracked.alias
    campaign.state = tracked.state
    campaign.domain_id = tracked.domain_id
    campaign.domain_name = tracked.domain_name
    campaign.group_id = tracked.group_id
    campaign.group_name = tracked.group_name
    campaign.traffic_source_id = tracked.traffic_source_id
    campaign.traffic_source_name = tracked.traffic_source_name
    campaign.layout_supported = tracked.streams is not None
    campaign.fetched_at = now


def merge_geo(stream: Stream, countries: list[str]) -> bool:
    """Returns True on a conflict: a pending draft and a change in the tracker."""
    pending = stream.draft_geo != stream.synced_geo
    changed = stream.synced_geo != countries
    stream.synced_geo = list(countries)
    if not pending:
        stream.draft_geo = list(countries)
        return False
    return changed


def merge_offers(stream: Stream, fetched: list[TrackerOffer], now: datetime) -> bool:
    """Returns True on a conflict: a pending draft and a change in the tracker."""
    pending = any(offer_pending(o) for o in stream.offers)
    by_id = {o.offer_id: o for o in stream.offers}
    fetched_ids = {f.offer_id for f in fetched}
    next_position = max((o.position for o in stream.offers), default=-1) + 1
    changed = False

    for item in fetched:
        row = by_id.get(item.offer_id)
        if row is None:
            # New in the tracker: the draft gains it too, whether or not it has pending edits.
            row = StreamOffer(
                offer_id=item.offer_id,
                name=item.name,
                position=next_position,
                synced_active=False,
                synced_share=None,
                draft_active=True,
                draft_share=item.share,
                pinned=False,
                pinned_share=None,
                removed_by=None,
                removed_at=None,
            )
            next_position += 1
            stream.offers.append(row)
        if not row.synced_active or row.synced_share != item.share:
            changed = True
        row.synced_active = True
        row.synced_share = item.share
        row.name = item.name

    for row in stream.offers:
        if row.synced_active and row.offer_id not in fetched_ids:
            changed = True
            row.synced_active = False
            row.synced_share = None
            if not pending:
                row.removed_by = REMOVED_BY_TRACKER
                row.removed_at = now

    if pending:
        return changed
    for row in stream.offers:
        row.draft_active = row.synced_active
        row.draft_share = row.synced_share
        if row.synced_active:
            row.removed_by = None
            row.removed_at = None
    return False


def merge_streams(campaign: Campaign, fetched: list[TrackerStream], now: datetime) -> bool:
    """Merges both streams; sets and returns the campaign's Conflict flag.

    A conflict stays flagged across fetches until the pending changes are pushed or cancelled.
    """
    by_role = {s.role: s for s in campaign.streams}
    conflict = False
    for item in fetched:
        stream = by_role.get(item.role)
        if stream is None:
            stream = Stream(role=item.role, synced_geo=None, draft_geo=None)
            campaign.streams.append(stream)
        stream.external_id = item.external_id
        stream.position = item.position
        stream.raw = item.raw
        if item.role == GEO:
            conflict = merge_geo(stream, item.geo or []) or conflict
        else:
            conflict = merge_offers(stream, item.offers, now) or conflict
    campaign.conflict = campaign_pending(campaign) and (campaign.conflict or conflict)
    return campaign.conflict
