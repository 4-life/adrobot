from typing import Any

import pytest

from app.tracker.keitaro.layout import detect_layout, parse_countries
from app.tracker.port import GEO, OFFERS, TrackerOffer

NAMES = {601: "Offer A"}


def geo_stream(**overrides: Any) -> dict[str, Any]:
    stream: dict[str, Any] = {
        "id": 501,
        "position": 1,
        "state": "active",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://example.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["AU"]}],
    }
    return stream | overrides


def offers_stream(**overrides: Any) -> dict[str, Any]:
    stream: dict[str, Any] = {
        "id": 502,
        "position": 2,
        "state": "active",
        "schema": "landings",
        "offers": [
            {"offer_id": 601, "share": 50, "state": "active"},
            {"offer_id": 602, "share": 50, "state": "active"},
        ],
    }
    return stream | overrides


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (["au", "NZ", "AU"], ["AU", "NZ"]),
        ('["AU","GB"]', ["AU", "GB"]),
        ("AU, NZ\nGB", ["AU", "NZ", "GB"]),
        (None, []),
        ({"unexpected": True}, []),
    ],
)
def test_parse_countries(payload: Any, expected: list[str]) -> None:
    assert parse_countries(payload) == expected


def test_detects_geo_then_offers_with_names() -> None:
    layout = detect_layout([offers_stream(), geo_stream()], NAMES)

    assert layout is not None
    geo, offers = layout
    assert (geo.role, geo.external_id, geo.geo) == (GEO, 501, ["AU"])
    assert (offers.role, offers.external_id) == (OFFERS, 502)
    assert offers.offers == [TrackerOffer(601, "Offer A", 50), TrackerOffer(602, "Offer 602", 50)]


def test_disabled_offers_are_not_active() -> None:
    stream = offers_stream(
        offers=[
            {"offer_id": 601, "share": 100, "state": "active"},
            {"offer_id": 602, "share": 0, "state": "disabled"},
        ]
    )
    layout = detect_layout([geo_stream(), stream], NAMES)

    assert layout is not None
    assert layout[1].offers == [TrackerOffer(601, "Offer A", 100)]


def test_deleted_streams_are_ignored() -> None:
    deleted = offers_stream(id=503, position=3, state="deleted")
    assert detect_layout([geo_stream(), offers_stream(), deleted], NAMES) is not None


@pytest.mark.parametrize(
    "streams",
    [
        [geo_stream()],
        [geo_stream(), offers_stream(), offers_stream(id=503, position=3)],
        [geo_stream(filters=[]), offers_stream()],
        [geo_stream(), offers_stream(schema="redirect")],
        [offers_stream(position=1), geo_stream(position=2)],
    ],
)
def test_other_layouts_are_unsupported(streams: list[dict[str, Any]]) -> None:
    assert detect_layout(streams, NAMES) is None
