"""Draft edits: add, remove, pin, bring back offers; set geo countries; cancel. No IO.

Nothing here reaches the tracker: edits change only the draft, and push (Phase 5) sends it.
Every offer change rebalances the stream's shares (app/campaigns/shares.py).
"""

import re
from datetime import datetime
from typing import Literal

from app.campaigns.shares import MAX_PIN, MIN_PIN, allocate
from app.models.campaign import ARCHIVED, Campaign, Stream, StreamOffer
from app.tracker.port import GEO, OFFERS

REMOVED_BY_ADROBOT = "adrobot"
COUNTRY_CODE = re.compile(r"[A-Z]{2}")

DraftErrorKind = Literal["not_found", "conflict", "invalid"]


class DraftError(Exception):
    def __init__(self, kind: DraftErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def ensure_editable(campaign: Campaign) -> None:
    if campaign.state == ARCHIVED:
        raise DraftError("conflict", "The campaign is archived in the tracker: read-only")
    if not campaign.layout_supported:
        raise DraftError("conflict", "The campaign isn't laid out as geo + offers: read-only")


def ensure_role(stream: Stream, role: str) -> None:
    if stream.role != role:
        raise DraftError("invalid", f"Stream {stream.id} is the {stream.role} stream, not {role}")


def active_offers(stream: Stream) -> list[StreamOffer]:
    return sorted((o for o in stream.offers if o.draft_active), key=lambda o: o.position)


def share_errors(stream: Stream) -> list[str]:
    """Why the offers stream's draft can't be pushed; empty when it can."""
    if stream.role != OFFERS:
        return []
    return allocate([o.pinned_share if o.pinned else None for o in active_offers(stream)]).errors


def rebalance(stream: Stream) -> None:
    active = active_offers(stream)
    allocation = allocate([o.pinned_share if o.pinned else None for o in active])
    for offer, share in zip(active, allocation.shares, strict=True):
        offer.draft_share = share
    for offer in stream.offers:
        if not offer.draft_active:
            offer.draft_share = None


def find_offer(stream: Stream, offer_id: int) -> StreamOffer:
    for offer in stream.offers:
        if offer.offer_id == offer_id:
            return offer
    raise DraftError("not_found", f"Offer {offer_id} isn't in this stream")


def _only_in_draft(offer: StreamOffer) -> bool:
    """Added in this draft and never in the tracker: removing or cancelling drops it."""
    return offer.draft_active and not offer.synced_active and offer.removed_by is None


def add_offer(stream: Stream, offer_id: int, name: str) -> None:
    ensure_role(stream, OFFERS)
    existing = next((o for o in stream.offers if o.offer_id == offer_id), None)
    if existing is not None:
        if existing.draft_active:
            raise DraftError("conflict", f"Offer {offer_id} is already in the stream")
        raise DraftError("conflict", f"Offer {offer_id} was removed: use Bring back")
    stream.offers.append(
        StreamOffer(
            offer_id=offer_id,
            name=name,
            position=max((o.position for o in stream.offers), default=-1) + 1,
            synced_active=False,
            synced_share=None,
            draft_active=True,
            draft_share=None,
            pinned=False,
            pinned_share=None,
            removed_by=None,
            removed_at=None,
        )
    )
    rebalance(stream)


def remove_offer(stream: Stream, offer_id: int, now: datetime) -> None:
    ensure_role(stream, OFFERS)
    offer = find_offer(stream, offer_id)
    if not offer.draft_active:
        raise DraftError("conflict", f"Offer {offer_id} is already removed")
    if _only_in_draft(offer):
        stream.offers.remove(offer)
    else:
        offer.draft_active = False
        offer.removed_by = REMOVED_BY_ADROBOT
        offer.removed_at = now
    rebalance(stream)


def restore_offer(stream: Stream, offer_id: int) -> None:
    """Bring back: into the draft with its last pin. `removed_by` stays until it's synced."""
    ensure_role(stream, OFFERS)
    offer = find_offer(stream, offer_id)
    if offer.draft_active:
        raise DraftError("conflict", f"Offer {offer_id} isn't removed")
    offer.draft_active = True
    rebalance(stream)


def set_pin(stream: Stream, offer_id: int, pinned: bool, pinned_share: int | None) -> None:
    ensure_role(stream, OFFERS)
    offer = find_offer(stream, offer_id)
    if not offer.draft_active:
        raise DraftError("conflict", f"Offer {offer_id} is removed: bring it back to pin it")
    if pinned:
        if pinned_share is None or not MIN_PIN <= pinned_share <= MAX_PIN:
            raise DraftError("invalid", f"A pinned share is {MIN_PIN}-{MAX_PIN}%")
        offer.pinned = True
        offer.pinned_share = pinned_share
    else:
        offer.pinned = False
        offer.pinned_share = None
    rebalance(stream)


def normalize_countries(countries: list[str]) -> list[str]:
    codes: list[str] = []
    for raw in countries:
        code = raw.strip().upper()
        if not COUNTRY_CODE.fullmatch(code):
            raise DraftError("invalid", f"{raw!r} isn't a two-letter country code")
        if code not in codes:
            codes.append(code)
    if not codes:
        raise DraftError("invalid", "The geo stream needs at least one country")
    return codes


def set_geo(stream: Stream, countries: list[str]) -> None:
    ensure_role(stream, GEO)
    stream.draft_geo = normalize_countries(countries)


def cancel(campaign: Campaign) -> bool:
    """Draft back to synced. Returns True when the whole campaign is a new draft to delete."""
    if campaign.is_new:
        return True
    for stream in campaign.streams:
        if stream.role == GEO:
            stream.draft_geo = None if stream.synced_geo is None else list(stream.synced_geo)
            continue
        for offer in list(stream.offers):
            if _only_in_draft(offer):
                stream.offers.remove(offer)
                continue
            offer.draft_active = offer.synced_active
            offer.draft_share = offer.synced_share
            if offer.synced_active:
                offer.removed_by = None
                offer.removed_at = None
    campaign.conflict = False
    return False
