"""How a draft differs from what the tracker has (synced): per offer, per geo stream, overall."""

from typing import Literal

from app.models.campaign import Campaign, Stream, StreamOffer
from app.tracker.port import GEO

OfferChange = Literal["added", "removed", "share"]


def offer_change(offer: StreamOffer) -> OfferChange | None:
    if offer.draft_active and not offer.synced_active:
        return "added"
    if offer.synced_active and not offer.draft_active:
        return "removed"
    if offer.draft_active and offer.draft_share != offer.synced_share:
        return "share"
    return None


def offer_pending(offer: StreamOffer) -> bool:
    return offer_change(offer) is not None


def geo_changes(stream: Stream) -> tuple[list[str], list[str]]:
    """The countries the draft adds and removes, each in draft / synced order."""
    synced = stream.synced_geo or []
    draft = stream.draft_geo or []
    return [c for c in draft if c not in synced], [c for c in synced if c not in draft]


def stream_pending(stream: Stream) -> bool:
    if stream.role == GEO:
        return stream.draft_geo != stream.synced_geo
    return any(offer_pending(o) for o in stream.offers)


def campaign_pending(campaign: Campaign) -> bool:
    return campaign.is_new or any(stream_pending(s) for s in campaign.streams)
