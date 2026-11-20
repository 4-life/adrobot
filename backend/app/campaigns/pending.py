"""Whether a draft differs from what the tracker has (synced)."""

from app.models.campaign import Campaign, Stream, StreamOffer
from app.tracker.port import GEO


def offer_pending(offer: StreamOffer) -> bool:
    if offer.draft_active != offer.synced_active:
        return True
    return offer.draft_active and offer.draft_share != offer.synced_share


def stream_pending(stream: Stream) -> bool:
    if stream.role == GEO:
        return stream.draft_geo != stream.synced_geo
    return any(offer_pending(o) for o in stream.offers)


def campaign_pending(campaign: Campaign) -> bool:
    return campaign.is_new or any(stream_pending(s) for s in campaign.streams)
