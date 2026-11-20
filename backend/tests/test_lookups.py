from app.api.lookups import active_out, search_offers
from app.tracker.port import LookupItem

OFFERS = [
    LookupItem(id=601, name="Sample Dating US"),
    LookupItem(id=602, name="Sample Crypto"),
    LookupItem(id=603, name="Sample Dating Old", active=False),
]


def ids(offers: list[LookupItem]) -> list[int]:
    return [o.id for o in offers]


def test_empty_query_returns_every_offer_archived_included() -> None:
    assert ids(search_offers(OFFERS, "")) == [601, 602, 603]


def test_matches_name_in_any_case() -> None:
    assert ids(search_offers(OFFERS, "dating")) == [601, 603]


def test_matches_exact_id() -> None:
    assert ids(search_offers(OFFERS, "602")) == [602]


def test_no_cap_on_the_number_of_results() -> None:
    many = [LookupItem(id=i, name=f"Offer {i}") for i in range(1, 201)]
    assert len(search_offers(many, "offer")) == 200


def test_selects_list_only_active_items() -> None:
    assert [(i.id, i.active) for i in active_out(OFFERS)] == [(601, True), (602, True)]
