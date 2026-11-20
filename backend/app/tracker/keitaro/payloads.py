"""Keitaro request payloads built from the port's types.

Built with `model_validate` on Keitaro's own field names (e.g. `schema`), so nothing depends
on how the generator named the Python attributes. Only the fields set here are sent.

The stream settings below follow the schema; the first real push confirms them against what
Keitaro stores (PLAN, Phase 4).
"""

from app.tracker.keitaro.models_overrides import CampaignRequest, StreamObject
from app.tracker.port import NewCampaign, NewGeoStream, NewOffersStream

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
            "offers": [
                {"offer_id": o.offer_id, "share": o.share, "state": "active"} for o in stream.offers
            ],
        }
    )
