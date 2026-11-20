from app.api.lookups import search_offers
from app.tracker.port import LookupItem

OFFERS = [
    LookupItem(id=601, name="Sample Dating US"),
    LookupItem(id=602, name="Sample Crypto"),
    LookupItem(id=603, name="Sample Dating Old", active=False),
]


def ids(offers: list[LookupItem]) -> list[int]:
    return [o.id for o in offers]


def test_matches_name_in_any_case() -> None:
    assert ids(search_offers(OFFERS, "dating")) == [601]


def test_matches_exact_id() -> None:
    assert ids(search_offers(OFFERS, "602")) == [602]


def test_empty_query_lists_active_offers() -> None:
    assert ids(search_offers(OFFERS, "")) == [601, 602]


def test_limit() -> None:
    assert ids(search_offers(OFFERS, "", limit=1)) == [601]
