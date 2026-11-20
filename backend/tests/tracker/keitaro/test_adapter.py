import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.tracker.keitaro.adapter import KeitaroTracker
from app.tracker.keitaro.client import KeitaroClient
from app.tracker.port import GEO, OFFERS, TrackerError, TrackerOffer, TrackerProvider

FIXTURES = Path(__file__).parents[2] / "fixtures" / "keitaro"

STREAMS = [
    {
        "id": 501,
        "position": 1,
        "state": "active",
        "schema": "redirect",
        "filters": [{"name": "country", "mode": "accept", "payload": ["AU"]}],
    },
    {
        "id": 502,
        "position": 2,
        "state": "active",
        "schema": "landings",
        "offers": [{"offer_id": 601, "share": 100, "state": "active"}],
    },
]
OFFERS_LIST = [
    {"id": 601, "name": "Sample Offer", "state": "active"},
    {"id": 602, "name": "Sample Old Offer", "state": "deleted"},
]
SOURCES = [{"id": 21, "name": "Sample Source", "state": "active"}]


def routes(request: httpx.Request) -> httpx.Response:
    path = request.url.path.removeprefix("/admin_api/v1")
    if path == "/campaigns":
        offset = int(request.url.params.get("offset", "0"))
        sample = json.loads((FIXTURES / "campaigns_sample.json").read_text())
        return httpx.Response(200, json=sample if offset == 0 else [])
    if path == "/campaigns/1001/streams":
        return httpx.Response(200, json=STREAMS)
    if path == "/campaigns/1002/streams":
        return httpx.Response(200, json=[STREAMS[1]])  # one stream: not AdRobot's layout
    if path == "/offers":
        return httpx.Response(200, json=OFFERS_LIST)
    if path == "/traffic_sources":
        return httpx.Response(200, json=SOURCES)
    return httpx.Response(404, json={"error": "Not found"})


def tracker(handler: Any = routes) -> TrackerProvider:
    transport = httpx.MockTransport(handler)
    return KeitaroTracker(KeitaroClient("https://kt.test", "key", retry_delay=0, transport=transport))


async def test_fetch_maps_campaigns_streams_and_names() -> None:
    async with tracker() as kt:
        campaigns = await kt.fetch_campaigns()

    first, second = campaigns
    assert (first.external_id, first.state) == (1001, "active")
    assert first.name == "test_sample_campaign1"
    assert (first.domain_id, first.domain_name) == (31, "https://example.com/")
    assert (first.group_id, first.group_name) == (11, "Sample group")
    assert (first.traffic_source_id, first.traffic_source_name) == (21, "Sample Source")
    assert first.streams is not None
    geo, offers = first.streams
    assert (geo.role, geo.geo) == (GEO, ["AU"])
    assert (offers.role, offers.offers) == (OFFERS, [TrackerOffer(601, "Sample Offer", 100)])

    assert second.state == "disabled"
    assert (second.group_id, second.traffic_source_id) == (None, None)
    assert second.streams is None


async def test_lookups_mark_inactive_items() -> None:
    async with tracker() as kt:
        offers = await kt.list_offers()

    assert [(o.id, o.active) for o in offers] == [(601, True), (602, False)]


async def test_keitaro_errors_become_tracker_errors() -> None:
    async with tracker(lambda _: httpx.Response(401, json={"error": "Bad key"})) as kt:
        with pytest.raises(TrackerError) as raised:
            await kt.list_domains()

    assert (raised.value.status, raised.value.message) == (401, "Bad key")
