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
    # [geo, offers]; None when the campaign isn't laid out that way (shown read-only).
    streams: list[TrackerStream] | None


@dataclass(frozen=True)
class LookupItem:
    id: int
    name: str
    active: bool = True


class TrackerError(Exception):
    """Any tracker failure. `status` is the tracker's HTTP status, 0 when nothing answered."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"tracker {status}: {message}")
        self.status = status
        self.message = message


class TrackerProvider(Protocol):
    async def fetch_campaigns(self) -> list[TrackerCampaign]:
        """Every campaign with its streams and offers (offer and source names resolved)."""
        ...

    async def list_offers(self) -> list[LookupItem]: ...

    async def list_domains(self) -> list[LookupItem]: ...

    async def list_groups(self) -> list[LookupItem]: ...

    async def list_sources(self) -> list[LookupItem]: ...

    async def aclose(self) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
