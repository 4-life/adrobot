"""Tracker lists for the dashboard's selects and offer search, cached for 60 s."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_tracker
from app.api.schemas import LookupOut
from app.tracker.cache import lookups
from app.tracker.port import LookupItem, TrackerProvider

router = APIRouter(prefix="/tracker")

Tracker = Annotated[TrackerProvider, Depends(get_tracker)]


def search_offers(offers: list[LookupItem], query: str) -> list[LookupItem]:
    """Every offer whose name contains the query (any case), or whose id is the query; an
    empty query matches them all. Archived ones too: the dashboard shows them, not pickable."""
    needle = query.strip().lower()
    if not needle:
        return list(offers)
    return [o for o in offers if needle in o.name.lower() or needle == str(o.id)]


def out(items: list[LookupItem]) -> list[LookupOut]:
    return [LookupOut(id=i.id, name=i.name, active=i.active) for i in items]


def active_out(items: list[LookupItem]) -> list[LookupOut]:
    """For the selects: only what a new campaign can use."""
    return out([i for i in items if i.active])


@router.get("/offers")
async def offers(tracker: Tracker, q: str = "") -> list[LookupOut]:
    return out(search_offers(await lookups.get("offers", tracker.list_offers), q))


@router.get("/domains")
async def domains(tracker: Tracker) -> list[LookupOut]:
    return active_out(await lookups.get("domains", tracker.list_domains))


@router.get("/groups")
async def groups(tracker: Tracker) -> list[LookupOut]:
    return active_out(await lookups.get("groups", tracker.list_groups))


@router.get("/sources")
async def sources(tracker: Tracker) -> list[LookupOut]:
    return active_out(await lookups.get("sources", tracker.list_sources))
