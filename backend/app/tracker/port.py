"""The tracker port: what AdRobot's core needs from an ad tracker, in AdRobot's own terms.

Merge, sync, push and the API depend only on this module. Each tracker (Keitaro today) is an
adapter package under app/tracker/<name>/ that implements `TrackerProvider` and maps its
vendor's API to and from these types. The adapter is picked in app/tracker/factory.py.
"""

from dataclasses import dataclass
from types import TracebackType
from typing import Any, Final, Literal, Protocol, Self

GEO: Final = "geo"
OFFERS: Final = "offers"
StreamRole = Literal["geo", "offers"]
CampaignState = Literal["active", "disabled", "archived"]


@dataclass(frozen=True)
class TrackerOffer:
    """An offer on a stream, with its share (%) of the stream's traffic."""

    offer_id: int
    name: str
    share: int


@dataclass(frozen=True)
class TrackerStream:
    external_id: int
    role: StreamRole
    position: int
    geo: list[str] | None  # geo stream: the countries sent to the redirect
    offers: list[TrackerOffer]  # offers stream: the active offers, in the tracker's order
    # The tracker's own stream data, opaque to the core. Stored, and handed back to the
    # adapter on push, so a push changes only what AdRobot manages.
    raw: dict[str, Any]


@dataclass(frozen=True)
class TrackerCampaign:
    external_id: int
    name: str
    alias: str
    state: CampaignState
    domain_id: int | None
    domain_name: str | None
    group_id: int | None
    group_name: str | None
    traffic_source_id: int | None
    traffic_source_name: str | None
    # [geo, offers]; None when the campaign isn't laid out that way (shown read-only), or when
    # its streams weren't read (`streams_fetched` False: keep what was known).
    streams: list[TrackerStream] | None
    streams_fetched: bool = True


@dataclass(frozen=True)
class LookupItem:
    id: int
    name: str
    active: bool = True


@dataclass(frozen=True)
class OfferShare:
    offer_id: int
    share: int


@dataclass(frozen=True)
class NewCampaign:
    name: str
    alias: str
    domain_id: int
    group_id: int | None
    traffic_source_id: int | None


@dataclass(frozen=True)
class NewGeoStream:
    """Sends visitors from `countries` to `redirect_url`; the campaign's first stream."""

    campaign_id: int  # the tracker's campaign id
    countries: list[str]
    redirect_url: str


@dataclass(frozen=True)
class NewOffersStream:
    """Splits all other traffic between `offers` by share; the campaign's second stream."""

    campaign_id: int  # the tracker's campaign id
    offers: list[OfferShare]


class TrackerError(Exception):
    """Any tracker failure. `status` is the tracker's HTTP status, 0 when nothing answered."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"tracker {status}: {message}")
        self.status = status
        self.message = message


class TrackerProvider(Protocol):
    async def fetch_campaigns(self, streams_prefix: str = "") -> list[TrackerCampaign]:
        """Every campaign (offer and source names resolved). Streams are read only for those
        whose name starts with `streams_prefix` ("": all); the rest have `streams_fetched`
        False. Reading streams is one request per campaign: on a shared tracker, the slow part.
        """
        ...

    async def fetch_campaign(self, campaign_id: int) -> TrackerCampaign | None:
        """One campaign, as `fetch_campaigns` has it; None when the tracker doesn't have it."""
        ...

    async def list_offers(self) -> list[LookupItem]: ...

    async def list_domains(self) -> list[LookupItem]: ...

    async def list_groups(self) -> list[LookupItem]: ...

    async def list_sources(self) -> list[LookupItem]: ...

    # Creating a campaign: one call per step, each returning the tracker's id, so a push that
    # fails partway resumes from the failed step (Phase 5).
    async def create_campaign(self, campaign: NewCampaign) -> int: ...

    async def create_geo_stream(self, stream: NewGeoStream) -> int: ...

    async def create_offers_stream(self, stream: NewOffersStream) -> int: ...

    # Pushing an existing campaign.
    async def get_streams(self, campaign_id: int) -> list[TrackerStream] | None:
        """The campaign's [geo, offers] streams as the tracker has them now; None when they
        aren't laid out that way any more."""
        ...

    async def push_offers(self, stream: TrackerStream, offers: list[OfferShare]) -> None:
        """Make `offers` the offers stream's offers (others on it are dropped)."""
        ...

    async def push_geo(self, stream: TrackerStream, countries: list[str]) -> None:
        """Make `countries` the geo stream's countries, leaving the rest of the stream as is."""
        ...

    async def aclose(self) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
