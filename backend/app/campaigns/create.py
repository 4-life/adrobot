"""New campaigns: built as a local draft (nothing reaches the tracker until Push). No IO."""

import re
import secrets
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.campaigns.drafts import DraftError, normalize_countries, rebalance
from app.models.campaign import Campaign, Stream, StreamOffer
from app.tracker.port import GEO, OFFERS

ALIAS_MAX = 40
ALIAS_SUFFIX_BYTES = 3  # 6 hex characters
ALIAS_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class OfferPick:
    offer_id: int
    name: str


def next_name(prefix: str, names: Iterable[str]) -> str:
    """`prefix` + (1 + the highest N already used as `prefix` + N)."""
    pattern = re.compile(re.escape(prefix) + r"(\d+)")
    used = [int(m.group(1)) for name in names if (m := pattern.fullmatch(name))]
    return f"{prefix}{max(used, default=0) + 1}"


def make_alias(name: str, token: Callable[[int], str] = secrets.token_hex) -> str:
    """URL-safe: the name as a slug plus a random suffix, e.g. `test-name-campaign3-1a2b3c`."""
    suffix = token(ALIAS_SUFFIX_BYTES)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = slug[: ALIAS_MAX - len(suffix) - 1].rstrip("-")
    return f"{slug}-{suffix}" if slug else suffix


def normalize_alias(alias: str) -> str:
    value = alias.strip().lower()
    if len(value) > ALIAS_MAX or not ALIAS_PATTERN.fullmatch(value):
        raise DraftError(
            "invalid",
            f"An alias is 1-{ALIAS_MAX} lowercase letters, digits and single dashes",
        )
    return value


def new_draft(
    *,
    name: str,
    alias: str,
    countries: list[str],
    domain_id: int,
    domain_name: str | None,
    group_id: int | None,
    group_name: str | None,
    traffic_source_id: int | None,
    traffic_source_name: str | None,
    offers: list[OfferPick],
) -> Campaign:
    if not name.strip():
        raise DraftError("invalid", "A campaign needs a name")
    if not offers:
        raise DraftError("invalid", "A campaign needs at least one offer")
    if len({o.offer_id for o in offers}) != len(offers):
        raise DraftError("invalid", "An offer is listed twice")

    # Every collection is set up front: after the commit, reading one the code never touched
    # would lazy-load it, which async SQLAlchemy refuses (MissingGreenlet).
    geo = Stream(
        role=GEO,
        position=1,
        synced_geo=None,
        draft_geo=normalize_countries(countries),
        raw=None,
        offers=[],
    )
    offers_stream = Stream(role=OFFERS, position=2, synced_geo=None, draft_geo=None, raw=None)
    offers_stream.offers = [
        StreamOffer(
            offer_id=o.offer_id,
            name=o.name,
            position=index,
            synced_active=False,
            synced_share=None,
            draft_active=True,
            draft_share=None,
            pinned=False,
            pinned_share=None,
            removed_by=None,
            removed_at=None,
        )
        for index, o in enumerate(offers)
    ]
    rebalance(offers_stream)
    return Campaign(
        external_id=None,
        name=name.strip(),
        alias=normalize_alias(alias),
        domain_id=domain_id,
        domain_name=domain_name,
        group_id=group_id,
        group_name=group_name,
        traffic_source_id=traffic_source_id,
        traffic_source_name=traffic_source_name,
        state="active",
        layout_supported=True,
        conflict=False,
        is_new=True,
        streams=[geo, offers_stream],
    )
