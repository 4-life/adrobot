import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.tracker.keitaro.client import NETWORK_ERROR, KeitaroClient, KeitaroError
from app.tracker.keitaro.models_overrides import CampaignRequest, OfferStreamRequest, StreamObject

FIXTURES = Path(__file__).parents[2] / "fixtures" / "keitaro"
API_KEY = "secret-test-key"

Handler = Callable[[httpx.Request], httpx.Response]


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def client(handler: Handler) -> KeitaroClient:
    return KeitaroClient(
        "https://kt.test/",
        API_KEY,
        retry_delay=0,
        transport=httpx.MockTransport(handler),
    )


STREAM = {
    "id": 7,
    "type": "regular",
    "name": "Offers",
    "campaign_id": 1001,
    "position": 2,
    "state": "active",
    "schema": "landings",
    "action_type": "http",
    "offers": [
        {"id": 1, "stream_id": 7, "offer_id": 11, "state": "active", "share": 50},
        {"id": 2, "stream_id": 7, "offer_id": 12, "state": "active", "share": 50},
    ],
}


async def test_sends_api_key_to_admin_api_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    async with client(handler) as kt:
        await kt.list_offers()

    assert seen[0].url.path == "/admin_api/v1/offers"
    assert seen[0].headers["Api-Key"] == API_KEY


async def test_campaigns_carry_domain_and_group_beyond_schema() -> None:
    sample = load("campaigns_sample.json")

    async with client(lambda _: httpx.Response(200, json=sample)) as kt:
        campaigns = await kt.list_campaigns()

    assert [c.id for c in campaigns] == [1001, 1002]
    assert campaigns[0].domain_id == 31
    assert campaigns[0].domain == "https://example.com/"
    assert campaigns[0].group == "Sample group"
    assert campaigns[1].domain_id is None


async def test_campaigns_are_paged_until_a_short_page() -> None:
    all_campaigns = [{"id": n, "name": f"c{n}"} for n in range(5)]
    offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        limit = int(request.url.params["limit"])
        offsets.append(offset)
        return httpx.Response(200, json=all_campaigns[offset : offset + limit])

    async with client(handler) as kt:
        campaigns = await kt.list_campaigns(page_size=2)

    assert [c.id for c in campaigns] == [0, 1, 2, 3, 4]
    assert offsets == [0, 2, 4]


async def test_stream_offers_are_parsed() -> None:
    async with client(lambda _: httpx.Response(200, json=STREAM)) as kt:
        stream = await kt.get_stream(7)

    assert stream.offers is not None
    assert [(o.offer_id, o.share) for o in stream.offers] == [(11, 50), (12, 50)]


async def test_read_retried_on_5xx() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(502)
        return httpx.Response(200, json=[])

    async with client(handler) as kt:
        assert await kt.list_domains() == []

    assert calls == 3


async def test_read_gives_up_after_retries() -> None:
    async with client(lambda _: httpx.Response(503, json={"error": "Down"})) as kt:
        with pytest.raises(KeitaroError) as raised:
            await kt.list_domains()

    assert raised.value.status == 503
    assert raised.value.message == "Down"


async def test_write_is_never_retried() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"error": "Boom"})

    async with client(handler) as kt:
        with pytest.raises(KeitaroError):
            await kt.create_campaign(CampaignRequest(name="x", alias="x"))

    assert calls == 1


async def test_4xx_error_message_from_body() -> None:
    async with client(lambda _: httpx.Response(404, json={"error": "Not found"})) as kt:
        with pytest.raises(KeitaroError) as raised:
            await kt.get_stream(999)

    assert raised.value.status == 404
    assert raised.value.message == "Not found"


async def test_network_error_hides_the_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with client(handler) as kt:
        with pytest.raises(KeitaroError) as raised:
            await kt.list_sources()

    assert raised.value.status == NETWORK_ERROR
    assert API_KEY not in str(raised.value)


async def test_update_stream_sends_only_set_fields() -> None:
    bodies: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=STREAM)

    payload = StreamObject(offers=[OfferStreamRequest(offer_id=11, share=100)])
    async with client(handler) as kt:
        await kt.update_stream(7, payload)

    assert bodies == [{"offers": [{"offer_id": 11, "share": 100}]}]


async def test_campaign_request_sends_group_id_as_integer() -> None:
    bodies: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"id": 1, "name": "x", "alias": "x"})

    async with client(handler) as kt:
        campaign = await kt.create_campaign(CampaignRequest(name="x", alias="x", group_id=11))

    assert bodies[0]["group_id"] == 11
    assert campaign.id == 1
