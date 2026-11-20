"""In-memory test doubles for the ports: core flows are tested without HTTP or a database."""

from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

from app.tracker.port import (
    GEO,
    OFFERS,
    LookupItem,
    NewCampaign,
    NewGeoStream,
    NewOffersStream,
    OfferShare,
    TrackerCampaign,
    TrackerError,
    TrackerOffer,
    TrackerStream,
)


class FakeStore:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class FakeTracker:
    """A tracker holding one campaign's streams; records every call, can fail on demand."""

    geo: list[str] = field(default_factory=lambda: ["AU"])
    offers: list[OfferShare] = field(default_factory=list)
    campaign_id: int = 1001
    next_id: int = 501
    calls: list[str] = field(default_factory=list)
    fail_on: str | None = None  # the call name that raises TrackerError once
    keep_removed: bool = False  # push_offers merges instead of replacing

    def _call(self, name: str) -> None:
        self.calls.append(name)
        if self.fail_on == name:
            self.fail_on = None
            raise TrackerError(500, f"{name} failed")

    def streams(self) -> list[TrackerStream]:
        return [
            TrackerStream(501, GEO, 1, list(self.geo), [], {"id": 501}),
            TrackerStream(
                502,
                OFFERS,
                2,
                None,
                [TrackerOffer(o.offer_id, f"Offer {o.offer_id}", o.share) for o in self.offers],
                {"id": 502},
            ),
        ]

    async def fetch_campaigns(self) -> list[TrackerCampaign]:
        raise NotImplementedError

    async def list_offers(self) -> list[LookupItem]:
        return []

    async def list_domains(self) -> list[LookupItem]:
        return []

    async def list_groups(self) -> list[LookupItem]:
        return []

    async def list_sources(self) -> list[LookupItem]:
        return []

    async def create_campaign(self, campaign: NewCampaign) -> int:
        self._call("create_campaign")
        return self.campaign_id

    async def create_geo_stream(self, stream: NewGeoStream) -> int:
        self._call("create_geo_stream")
        self.geo = list(stream.countries)
        return 501

    async def create_offers_stream(self, stream: NewOffersStream) -> int:
        self._call("create_offers_stream")
        self.offers = list(stream.offers)
        return 502

    async def get_streams(self, campaign_id: int) -> list[TrackerStream] | None:
        self._call("get_streams")
        return self.streams()

    async def push_offers(self, stream: TrackerStream, offers: list[OfferShare]) -> None:
        self._call("push_offers")
        if self.keep_removed:
            sent = {o.offer_id for o in offers}
            self.offers = [o for o in self.offers if o.offer_id not in sent] + offers
        else:
            self.offers = list(offers)

    async def push_geo(self, stream: TrackerStream, countries: list[str]) -> None:
        self._call("push_geo")
        self.geo = list(countries)

    async def aclose(self) -> None:
        return None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None
