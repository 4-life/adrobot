"""An in-memory tracker for local testing (`TRACKER=fake`): no Keitaro, nothing leaves the API.

It implements the same port as the Keitaro adapter, so fetch, create, push, conflicts and the
offer search all behave as with a real tracker. Seeded with sample data (made-up names and
ids); every change lives in the API process's memory and is gone on restart.
"""

from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

from app.config import settings
from app.tracker.port import (
    GEO,
    OFFERS,
    CampaignState,
    LookupItem,
    NewCampaign,
    NewGeoStream,
    NewOffersStream,
    OfferShare,
    TrackerCampaign,
    TrackerOffer,
    TrackerStream,
)

SAMPLE_OFFERS = 20
ARCHIVED_OFFERS = {18, 19, 20}  # sample offers 18-20 are archived: listed, not usable


@dataclass
class _Stream:
    id: int
    role: str
    position: int
    geo: list[str] = field(default_factory=list)
    offers: list[OfferShare] = field(default_factory=list)


@dataclass
class _Campaign:
    id: int
    name: str
    alias: str
    state: CampaignState
    domain_id: int | None
    group_id: int | None
    source_id: int | None
    streams: list[_Stream] = field(default_factory=list)


@dataclass
class _State:
    offers: list[LookupItem]
    domains: list[LookupItem]
    groups: list[LookupItem]
    sources: list[LookupItem]
    campaigns: dict[int, _Campaign] = field(default_factory=dict)
    next_id: int = 5000

    def new_id(self) -> int:
        self.next_id += 1
        return self.next_id


def _seeded(prefix: str) -> _State:
    offers = [
        LookupItem(id=600 + n, name=f"Sample offer {n}", active=n not in ARCHIVED_OFFERS)
        for n in range(1, SAMPLE_OFFERS + 1)
    ]
    state = _State(
        offers=offers,
        domains=[
            LookupItem(id=31, name="https://example.com/"),
            LookupItem(id=32, name="https://example.org/"),
        ],
        groups=[LookupItem(id=11, name="Sample group"), LookupItem(id=12, name="Other group")],
        sources=[LookupItem(id=21, name="Sample source"), LookupItem(id=22, name="Other source")],
    )
    state.campaigns = {
        1001: _Campaign(
            id=1001,
            name=f"{prefix}1",
            alias="sample-one",
            state="active",
            domain_id=31,
            group_id=11,
            source_id=21,
            streams=[
                _Stream(id=1101, role=GEO, position=1, geo=["AU"]),
                _Stream(
                    id=1102,
                    role=OFFERS,
                    position=2,
                    offers=[OfferShare(601, 34), OfferShare(602, 33), OfferShare(603, 33)],
                ),
            ],
        ),
        1002: _Campaign(
            id=1002,
            name="other_team_campaign",
            alias="other-team",
            state="active",
            domain_id=32,
            group_id=12,
            source_id=22,
            streams=[
                _Stream(id=1201, role=GEO, position=1, geo=["AU", "NZ"]),
                _Stream(id=1202, role=OFFERS, position=2, offers=[OfferShare(604, 100)]),
            ],
        ),
        1003: _Campaign(
            id=1003,
            name="unsupported_layout_campaign",
            alias="unsupported",
            state="disabled",
            domain_id=31,
            group_id=None,
            source_id=None,
            streams=[_Stream(id=1301, role=OFFERS, position=1, offers=[OfferShare(605, 100)])],
        ),
    }
    return state


_STATE: _State | None = None


def state() -> _State:
    """One shared state per API process, seeded on first use."""
    global _STATE
    if _STATE is None:
        _STATE = _seeded(settings.campaign_name_prefix)
    return _STATE


def reset() -> None:
    """Back to the seed (tests)."""
    global _STATE
    _STATE = None


def _name(items: list[LookupItem], item_id: int | None) -> str | None:
    return next((i.name for i in items if i.id == item_id), None)


class InMemoryTracker:
    def __init__(self, data: _State | None = None) -> None:
        self._s = data or state()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def aclose(self) -> None:
        return None

    # --- reads ---

    def _streams(self, campaign: _Campaign) -> list[TrackerStream] | None:
        by_role = {s.role: s for s in campaign.streams}
        if len(campaign.streams) != 2 or set(by_role) != {GEO, OFFERS}:
            return None
        names = {o.id: o.name for o in self._s.offers}
        geo, offers = by_role[GEO], by_role[OFFERS]
        return [
            TrackerStream(geo.id, GEO, geo.position, list(geo.geo), [], {"id": geo.id}),
            TrackerStream(
                offers.id,
                OFFERS,
                offers.position,
                None,
                [
                    TrackerOffer(o.offer_id, names.get(o.offer_id, f"Offer {o.offer_id}"), o.share)
                    for o in offers.offers
                ],
                {"id": offers.id},
            ),
        ]

    def _campaign(self, c: _Campaign, with_streams: bool = True) -> TrackerCampaign:
        return TrackerCampaign(
            external_id=c.id,
            name=c.name,
            alias=c.alias,
            state=c.state,
            domain_id=c.domain_id,
            domain_name=_name(self._s.domains, c.domain_id),
            group_id=c.group_id,
            group_name=_name(self._s.groups, c.group_id),
            traffic_source_id=c.source_id,
            traffic_source_name=_name(self._s.sources, c.source_id),
            streams=self._streams(c) if with_streams else None,
            streams_fetched=with_streams,
        )

    async def fetch_campaigns(self, streams_prefix: str = "") -> list[TrackerCampaign]:
        return [
            self._campaign(c, with_streams=c.name.startswith(streams_prefix))
            for c in self._s.campaigns.values()
        ]

    async def fetch_campaign(self, campaign_id: int) -> TrackerCampaign | None:
        campaign = self._s.campaigns.get(campaign_id)
        return self._campaign(campaign) if campaign else None

    async def list_offers(self) -> list[LookupItem]:
        return list(self._s.offers)

    async def list_domains(self) -> list[LookupItem]:
        return list(self._s.domains)

    async def list_groups(self) -> list[LookupItem]:
        return list(self._s.groups)

    async def list_sources(self) -> list[LookupItem]:
        return list(self._s.sources)

    async def get_streams(self, campaign_id: int) -> list[TrackerStream] | None:
        campaign = self._s.campaigns.get(campaign_id)
        return self._streams(campaign) if campaign else None

    # --- writes ---

    async def create_campaign(self, campaign: NewCampaign) -> int:
        new_id = self._s.new_id()
        self._s.campaigns[new_id] = _Campaign(
            id=new_id,
            name=campaign.name,
            alias=campaign.alias,
            state="active",
            domain_id=campaign.domain_id,
            group_id=campaign.group_id,
            source_id=campaign.traffic_source_id,
        )
        return new_id

    async def create_geo_stream(self, stream: NewGeoStream) -> int:
        new_id = self._s.new_id()
        self._s.campaigns[stream.campaign_id].streams.append(
            _Stream(id=new_id, role=GEO, position=1, geo=list(stream.countries))
        )
        return new_id

    async def create_offers_stream(self, stream: NewOffersStream) -> int:
        new_id = self._s.new_id()
        self._s.campaigns[stream.campaign_id].streams.append(
            _Stream(id=new_id, role=OFFERS, position=2, offers=list(stream.offers))
        )
        return new_id

    def _stream(self, stream_id: int) -> _Stream:
        for campaign in self._s.campaigns.values():
            for item in campaign.streams:
                if item.id == stream_id:
                    return item
        raise KeyError(stream_id)

    async def push_offers(self, stream: TrackerStream, offers: list[OfferShare]) -> None:
        self._stream(stream.external_id).offers = list(offers)

    async def push_geo(self, stream: TrackerStream, countries: list[str]) -> None:
        self._stream(stream.external_id).geo = list(countries)


def create() -> InMemoryTracker:
    return InMemoryTracker()
