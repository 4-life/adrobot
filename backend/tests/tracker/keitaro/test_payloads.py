import json
from typing import Any

import httpx

from app.tracker.keitaro import payloads
from app.tracker.keitaro.adapter import KeitaroTracker
from app.tracker.keitaro.client import KeitaroClient
from app.tracker.port import NewCampaign, NewGeoStream, NewOffersStream, OfferShare

CAMPAIGN = NewCampaign(
    name="test_name_campaign1",
    alias="test-name-campaign1-1a2b3c",
    domain_id=31,
    group_id=None,
    traffic_source_id=21,
)
GEO = NewGeoStream(campaign_id=1001, countries=["AU", "NZ"], redirect_url="https://example.com")
OFFERS = NewOffersStream(campaign_id=1001, offers=[OfferShare(601, 60), OfferShare(602, 40)])


def sent(model: Any) -> Any:
    return model.model_dump(mode="json", by_alias=True, exclude_unset=True)


def test_campaign_payload_sends_only_what_is_set() -> None:
    assert sent(payloads.campaign_request(CAMPAIGN)) == {
        "name": "test_name_campaign1",
        "alias": "test-name-campaign1-1a2b3c",
        "type": "position",
        "state": "active",
        "domain_id": 31,
        "traffic_source_id": 21,
    }


def test_geo_stream_payload() -> None:
    assert sent(payloads.geo_stream_request(GEO)) == {
        "campaign_id": 1001,
        "type": "regular",
        "name": "Geo",
        "position": 1,
        "state": "active",
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://example.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["AU", "NZ"]}],
    }


def test_offers_stream_payload() -> None:
    body = sent(payloads.offers_stream_request(OFFERS))

    assert (body["position"], body["schema"]) == (2, "landings")
    assert "filters" not in body
    assert body["offers"] == [
        {"offer_id": 601, "share": 60, "state": "active"},
        {"offer_id": 602, "share": 40, "state": "active"},
    ]


async def test_create_steps_return_the_tracker_ids() -> None:
    requests: list[tuple[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append((request.url.path, body))
        if request.url.path.endswith("/campaigns"):
            return httpx.Response(200, json={"id": 1001, "name": body["name"]})
        return httpx.Response(200, json={"id": 500 + body["position"]})

    client = KeitaroClient("https://kt.test", "key", transport=httpx.MockTransport(handler))
    async with KeitaroTracker(client) as kt:
        ids = (
            await kt.create_campaign(CAMPAIGN),
            await kt.create_geo_stream(GEO),
            await kt.create_offers_stream(OFFERS),
        )

    assert ids == (1001, 501, 502)
    assert [path for path, _ in requests] == [
        "/admin_api/v1/campaigns",
        "/admin_api/v1/streams",
        "/admin_api/v1/streams",
    ]
