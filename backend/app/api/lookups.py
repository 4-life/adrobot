"""Tracker lists for the dashboard's selects and offer search, cached for 60 s."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_tracker
from app.api.schemas import LookupOut
from app.tracker.cache import lookups
from app.tracker.port import LookupItem, TrackerProvider

router = APIRouter(prefix="/tracker")

Tracker = Annotated[TrackerProvider, Depends(get_tracker)]

OFFER_SEARCH_LIMIT = 50


def search_offers(
    offers: list[LookupItem], query: str, limit: int = OFFER_SEARCH_LIMIT
) -> list[LookupItem]:
    """Active offers whose name contains the query (any case), or whose id is the query."""
    needle = query.strip().lower()
    found: list[LookupItem] = []
    for offer in offers:
        if not offer.active:
            continue
        if needle and needle not in offer.name.lower() and needle != str(offer.id):
            continue
        found.append(offer)
        if len(found) == limit:
            break
    return found


def out(items: list[LookupItem]) -> list[LookupOut]:
    return [LookupOut(id=i.id, name=i.name) for i in items]


@router.get("/offers")
async def offers(tracker: Tracker, q: str = "") -> list[LookupOut]:
    return out(search_offers(await lookups.get("offers", tracker.list_offers), q))


@router.get("/domains")
async def domains(tracker: Tracker) -> list[LookupOut]:
    return out(await lookups.get("domains", tracker.list_domains))


@router.get("/groups")
async def groups(tracker: Tracker) -> list[LookupOut]:
    return out(await lookups.get("groups", tracker.list_groups))


@router.get("/sources")
async def sources(tracker: Tracker) -> list[LookupOut]:
    return out(await lookups.get("sources", tracker.list_sources))
