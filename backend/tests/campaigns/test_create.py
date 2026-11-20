import pytest
from sqlalchemy import inspect

from app.campaigns.create import OfferPick, make_alias, new_draft, next_name, normalize_alias
from app.campaigns.drafts import DraftError
from app.campaigns.pending import campaign_pending, offer_change
from app.models.campaign import Campaign
from app.tracker.port import GEO, OFFERS

PREFIX = "test_name_campaign"


def fixed_token(_: int) -> str:
    return "1a2b3c"


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        ([], "test_name_campaign1"),
        (["test_name_campaign1", "test_name_campaign2"], "test_name_campaign3"),
        (["test_name_campaign9", "test_name_campaign10"], "test_name_campaign11"),
        (["test_name_campaign2", "test_name_campaignX", "other7"], "test_name_campaign3"),
    ],
)
def test_next_name(names: list[str], expected: str) -> None:
    assert next_name(PREFIX, names) == expected


def test_alias_is_a_slug_with_a_random_suffix() -> None:
    assert make_alias("Test_Name Campaign3", fixed_token) == "test-name-campaign3-1a2b3c"
    assert make_alias("!!!", fixed_token) == "1a2b3c"
    assert len(make_alias("x" * 100, fixed_token)) <= 40


@pytest.mark.parametrize("alias", ["", "Has Space", "a--b", "-a", "ä", "x" * 41])
def test_invalid_alias_is_refused(alias: str) -> None:
    with pytest.raises(DraftError, match="alias"):
        normalize_alias(alias)


def test_alias_is_normalized() -> None:
    assert normalize_alias(" My-Alias-1 ") == "my-alias-1"


def draft(offers: list[OfferPick], countries: list[str] | None = None) -> Campaign:
    return new_draft(
        name="test_name_campaign1",
        alias="test-name-campaign1-1a2b3c",
        countries=countries or ["au"],
        domain_id=31,
        domain_name="https://example.com/",
        group_id=None,
        group_name=None,
        traffic_source_id=21,
        traffic_source_name="Sample Source",
        offers=offers,
    )


def test_new_draft_has_both_streams_and_equal_shares() -> None:
    campaign = draft([OfferPick(601, "A"), OfferPick(602, "B"), OfferPick(603, "C")])

    assert campaign.is_new and campaign.external_id is None
    geo, offers = campaign.streams
    assert (geo.role, geo.draft_geo, geo.synced_geo) == (GEO, ["AU"], None)
    assert offers.role == OFFERS
    assert [(o.offer_id, o.draft_share) for o in offers.offers] == [(601, 34), (602, 33), (603, 33)]
    assert all(offer_change(o) == "added" for o in offers.offers)
    assert campaign_pending(campaign)


@pytest.mark.parametrize(
    ("offers", "error"),
    [
        ([], "at least one offer"),
        ([OfferPick(601, "A"), OfferPick(601, "A")], "listed twice"),
    ],
)
def test_invalid_offers_are_refused(offers: list[OfferPick], error: str) -> None:
    with pytest.raises(DraftError, match=error):
        draft(offers)


def test_invalid_geo_is_refused() -> None:
    with pytest.raises(DraftError, match="two-letter"):
        draft([OfferPick(601, "A")], countries=["Australia"])


def test_new_draft_has_every_collection_loaded() -> None:
    """Async SQLAlchemy can't lazy-load: a collection never set would fail after the commit."""
    campaign = draft([OfferPick(601, "A")])

    assert "streams" not in inspect(campaign).unloaded
    for stream in campaign.streams:
        assert "offers" not in inspect(stream).unloaded
