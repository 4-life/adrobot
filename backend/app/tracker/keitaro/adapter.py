"""The Keitaro adapter: implements the tracker port on top of the Keitaro Admin API.

The only module the rest of AdRobot reaches Keitaro through (via app/tracker/factory.py).
Keitaro's models and errors never leave this package: they're mapped to app/tracker/port.py.
"""

import asyncio
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self

from pydantic import ValidationError

from app.tracker.keitaro import payloads
from app.tracker.keitaro.client import KeitaroClient, KeitaroError
from app.tracker.keitaro.layout import detect_layout
from app.tracker.keitaro.models_overrides import Campaign
from app.tracker.port import (
    CampaignState,
    LookupItem,
    NewCampaign,
    NewGeoStream,
    NewOffersStream,
    OfferShare,
    TrackerCampaign,
    TrackerError,
    TrackerStream,
)

STREAM_FETCH_CONCURRENCY = 8
UNEXPECTED_DATA = 502  # TrackerError.status: Keitaro answered, but not as its schema says
ACTIVE = "active"
KEITARO_ARCHIVED = "deleted"
STATES: dict[str, CampaignState] = {
    "active": "active",
    "disabled": "disabled",
    KEITARO_ARCHIVED: "archived",
}


async def _translated[T](call: Awaitable[T]) -> T:
    """Keitaro's errors, and data that doesn't match its schema, become TrackerError."""
    try:
        return await call
    except KeitaroError as error:
        raise TrackerError(error.status, error.message) from error
    except ValidationError as error:
        raise TrackerError(UNEXPECTED_DATA, unexpected_data(error)) from error


def unexpected_data(error: ValidationError) -> str:
    """Where and how Keitaro's data didn't match: the field path and pydantic's message, with
    no values (they can be real tracker data)."""
    first = error.errors(include_input=False, include_url=False)[0]
    path = ".".join(str(part) for part in first["loc"])
    more = f" (+{error.error_count() - 1} more)" if error.error_count() > 1 else ""
    return (
        f"Keitaro sent data that doesn't match its schema at {error.title} {path}: "
        f"{first['msg']}{more}. Add a fix in models_overrides.py"
    )


def _lookup(rows: list[tuple[int | None, str | None, str | None]]) -> list[LookupItem]:
    return [
        LookupItem(id=i, name=name or f"#{i}", active=(state or ACTIVE) == ACTIVE)
        for i, name, state in rows
        if i is not None
    ]


def to_campaign(
    kt: Campaign,
    streams: list[dict[str, Any]] | None,
    offer_names: dict[int, str],
    source_names: dict[int, str],
) -> TrackerCampaign:
    if kt.id is None:
        raise ValueError("a Keitaro campaign without an id")
    source_id = kt.traffic_source_id or None
    return TrackerCampaign(
        external_id=kt.id,
        name=kt.name or "",
        alias=kt.alias or "",
        state=STATES.get(kt.state or ACTIVE, "active"),
        domain_id=kt.domain_id,
        domain_name=kt.domain or None,
        group_id=kt.group_id or None,
        group_name=kt.group or None,
        traffic_source_id=source_id,
        traffic_source_name=source_names.get(source_id) if source_id else None,
        streams=detect_layout(streams, offer_names) if streams is not None else None,
    )


class KeitaroTracker:
    def __init__(self, client: KeitaroClient) -> None:
        self._kt = client

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._kt.aclose()

    async def fetch_campaigns(self) -> list[TrackerCampaign]:
        return await _translated(self._fetch_campaigns())

    async def _fetch_campaigns(self) -> list[TrackerCampaign]:
        campaigns, offers, sources = await asyncio.gather(
            self._kt.list_campaigns(), self._kt.list_offers(), self._kt.list_sources()
        )
        offer_names = {o.id: o.name for o in offers if o.id is not None and o.name}
        source_names = {s.id: s.name for s in sources if s.id is not None and s.name}
        live = [c.id for c in campaigns if c.id is not None and c.state != KEITARO_ARCHIVED]
        streams = await self._streams_of(live)
        return [
            to_campaign(c, streams.get(c.id), offer_names, source_names)
            for c in campaigns
            if c.id is not None
        ]

    async def _streams_of(self, campaign_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
        """Each campaign's streams as raw JSON, a few campaigns at a time."""
        limit = asyncio.Semaphore(STREAM_FETCH_CONCURRENCY)

        async def one(campaign_id: int) -> tuple[int, list[dict[str, Any]]]:
            async with limit:
                return campaign_id, await self._raw_streams(campaign_id)

        return dict(await asyncio.gather(*(one(i) for i in campaign_ids)))

    async def _raw_streams(self, campaign_id: int) -> list[dict[str, Any]]:
        streams = await self._kt.list_streams(campaign_id)
        return [s.model_dump(mode="json", by_alias=True, exclude_unset=True) for s in streams]

    async def get_streams(self, campaign_id: int) -> list[TrackerStream] | None:
        return await _translated(self._get_streams(campaign_id))

    async def _get_streams(self, campaign_id: int) -> list[TrackerStream] | None:
        raws, offers = await asyncio.gather(self._raw_streams(campaign_id), self._kt.list_offers())
        names = {o.id: o.name for o in offers if o.id is not None and o.name}
        return detect_layout(raws, names)

    async def push_offers(self, stream: TrackerStream, offers: list[OfferShare]) -> None:
        request = payloads.offers_update_request(offers)
        await _translated(self._kt.update_stream(stream.external_id, request))

    async def push_geo(self, stream: TrackerStream, countries: list[str]) -> None:
        request = payloads.geo_update_request(stream.raw, countries)
        await _translated(self._kt.update_stream(stream.external_id, request))

    async def list_offers(self) -> list[LookupItem]:
        offers = await _translated(self._kt.list_offers())
        return _lookup([(o.id, o.name, o.state) for o in offers])

    async def list_domains(self) -> list[LookupItem]:
        domains = await _translated(self._kt.list_domains())
        return _lookup([(d.id, d.name, d.state) for d in domains])

    async def list_groups(self) -> list[LookupItem]:
        groups = await _translated(self._kt.list_groups())
        return _lookup([(g.id, g.name, None) for g in groups])

    async def list_sources(self) -> list[LookupItem]:
        sources = await _translated(self._kt.list_sources())
        return _lookup([(s.id, s.name, s.state) for s in sources])

    async def create_campaign(self, campaign: NewCampaign) -> int:
        created = await _translated(self._kt.create_campaign(payloads.campaign_request(campaign)))
        return _required_id(created.id, "campaign")

    async def create_geo_stream(self, stream: NewGeoStream) -> int:
        created = await _translated(self._kt.create_stream(payloads.geo_stream_request(stream)))
        return _required_id(created.id, "geo stream")

    async def create_offers_stream(self, stream: NewOffersStream) -> int:
        request = payloads.offers_stream_request(stream)
        created = await _translated(self._kt.create_stream(request))
        return _required_id(created.id, "offers stream")


def _required_id(value: int | None, what: str) -> int:
    if value is None:
        raise TrackerError(502, f"Keitaro created the {what} but returned no id")
    return value


def create(factory: Callable[[], KeitaroClient] = KeitaroClient.from_settings) -> KeitaroTracker:
    return KeitaroTracker(factory())
