"""Keitaro request payloads built from the port's types.

Built with `model_validate` on Keitaro's own field names (e.g. `schema`), so nothing depends
on how the generator named the Python attributes. Only the fields set here are sent.

The stream settings below follow the schema; the first real push confirms them against what
Keitaro stores (PLAN, Phase 4).
"""

from typing import Any

from app.tracker.keitaro.layout import COUNTRY_FILTER
from app.tracker.keitaro.models_overrides import CampaignRequest, StreamObject
from app.tracker.port import NewCampaign, NewGeoStream, NewOffersStream, OfferShare

FILTER_FIELDS = ("id", "name", "mode", "payload")

GEO_STREAM_NAME = "Geo"
OFFERS_STREAM_NAME = "Offers"
GEO_POSITION = 1
OFFERS_POSITION = 2


def campaign_request(campaign: NewCampaign) -> CampaignRequest:
    fields: dict[str, object] = {
        "name": campaign.name,
        "alias": campaign.alias,
        "type": "position",  # streams are matched in position order: geo first
        "state": "active",
        "domain_id": campaign.domain_id,
    }
    if campaign.group_id is not None:
        fields["group_id"] = campaign.group_id
    if campaign.traffic_source_id is not None:
        fields["traffic_source_id"] = campaign.traffic_source_id
    return CampaignRequest.model_validate(fields)


def geo_stream_request(stream: NewGeoStream) -> StreamObject:
    return StreamObject.model_validate(
        {
            "campaign_id": stream.campaign_id,
            "type": "regular",
            "name": GEO_STREAM_NAME,
            "position": GEO_POSITION,
            "state": "active",
            "schema": "redirect",
            "action_type": "http",
            "action_payload": stream.redirect_url,
            "filters": [{"name": "country", "mode": "accept", "payload": stream.countries}],
        }
    )


def offers_stream_request(stream: NewOffersStream) -> StreamObject:
    return StreamObject.model_validate(
        {
            "campaign_id": stream.campaign_id,
            "type": "regular",  # no filters: takes everyone the geo stream didn't
            "name": OFFERS_STREAM_NAME,
            "position": OFFERS_POSITION,
            "state": "active",
            "schema": "landings",
            "action_type": "http",
            "offers": _offers(stream.offers),
        }
    )


def _offers(offers: list[OfferShare]) -> list[dict[str, object]]:
    return [{"offer_id": o.offer_id, "share": o.share, "state": "active"} for o in offers]


def offers_update_request(offers: list[OfferShare]) -> StreamObject:
    """PUT /streams/{id}: only `offers`, so nothing else on the stream changes."""
    return StreamObject.model_validate({"offers": _offers(offers)})


def geo_update_request(raw: dict[str, Any], countries: list[str]) -> StreamObject:
    """PUT /streams/{id}: only `filters`. Every filter the stream has (from `raw`) is kept
    with its id; the country filter gets `countries` (added if the stream has none)."""
    filters: list[dict[str, Any]] = []
    for item in raw.get("filters") or []:
        kept = {k: item[k] for k in FILTER_FIELDS if k in item}
        if item.get("name") == COUNTRY_FILTER:
            kept["payload"] = countries
        filters.append(kept)
    if not any(f.get("name") == COUNTRY_FILTER for f in filters):
        filters.append({"name": COUNTRY_FILTER, "mode": "accept", "payload": countries})
    return StreamObject.model_validate({"filters": filters})
