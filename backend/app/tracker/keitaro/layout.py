"""Recognises AdRobot's campaign layout in Keitaro's streams: geo stream, then offers stream.

Works on the raw stream JSON (as Keitaro sent it), so nothing depends on generated field names.
"""

import json
from collections.abc import Mapping
from typing import Any

from app.tracker.port import GEO, OFFERS, TrackerOffer, TrackerStream

COUNTRY_FILTER = "country"
DELETED = "deleted"
ACTIVE = "active"


def parse_countries(payload: Any) -> list[str]:
    """A country filter's payload as upper-case codes, in order, without repeats.

    Keitaro sends a list; a JSON-encoded list or a comma/newline separated string is accepted too.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            payload = payload.replace("\n", ",").split(",")
    if not isinstance(payload, list):
        return []
    codes: list[str] = []
    for item in payload:
        code = str(item).strip().upper()
        if code and code not in codes:
            codes.append(code)
    return codes


def country_filter(raw: dict[str, Any]) -> list[str] | None:
    for item in raw.get("filters") or []:
        if isinstance(item, dict) and item.get("name") == COUNTRY_FILTER:
            return parse_countries(item.get("payload"))
    return None


def offer_name(offer_id: int, names: Mapping[int, str]) -> str:
    return names.get(offer_id) or f"Offer {offer_id}"


def active_offers(raw: dict[str, Any], names: Mapping[int, str]) -> list[TrackerOffer]:
    offers: list[TrackerOffer] = []
    for item in raw.get("offers") or []:
        if item.get("state", ACTIVE) != ACTIVE:
            continue
        offer_id = int(item["offer_id"])
        name = offer_name(offer_id, names)
        offers.append(TrackerOffer(offer_id=offer_id, name=name, share=int(item["share"])))
    return offers


def detect_layout(
    streams: list[dict[str, Any]], names: Mapping[int, str]
) -> list[TrackerStream] | None:
    """The geo and offers streams, or None when the campaign isn't laid out that way.

    Supported: exactly two live streams; the first has a country filter and no offers, the
    second isn't a plain redirect.
    """
    live = sorted(
        (s for s in streams if s.get("state") != DELETED),
        key=lambda s: int(s.get("position") or 0),
    )
    if len(live) != 2:
        return None
    geo_raw, offers_raw = live
    countries = country_filter(geo_raw)
    if countries is None or geo_raw.get("offers"):
        return None
    if offers_raw.get("schema") == "redirect":
        return None
    return [
        TrackerStream(
            external_id=int(geo_raw["id"]),
            role=GEO,
            position=int(geo_raw.get("position") or 0),
            geo=countries,
            offers=[],
            raw=geo_raw,
        ),
        TrackerStream(
            external_id=int(offers_raw["id"]),
            role=OFFERS,
            position=int(offers_raw.get("position") or 0),
            geo=None,
            offers=active_offers(offers_raw, names),
            raw=offers_raw,
        ),
    ]
