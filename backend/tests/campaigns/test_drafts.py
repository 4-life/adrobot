from datetime import UTC, datetime

import pytest

from app.campaigns import drafts
from app.campaigns.drafts import DraftError
from app.campaigns.pending import campaign_pending, geo_changes, offer_change
from app.models.campaign import ARCHIVED, Campaign, Stream, StreamOffer
from app.tracker.port import GEO, OFFERS

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def synced_offer(offer_id: int, share: int, position: int) -> StreamOffer:
    return StreamOffer(
        offer_id=offer_id,
        name=f"Offer {offer_id}",
        position=position,
        synced_active=True,
        synced_share=share,
        draft_active=True,
        draft_share=share,
        pinned=False,
        pinned_share=None,
        removed_by=None,
        removed_at=None,
    )


def campaign() -> Campaign:
    """In sync with the tracker: geo AU, offers 601 / 602 at 50 / 50."""
    geo = Stream(role=GEO, position=1, synced_geo=["AU"], draft_geo=["AU"])
    offers = Stream(role=OFFERS, position=2, synced_geo=None, draft_geo=None)
    offers.offers = [synced_offer(601, 50, 0), synced_offer(602, 50, 1)]
    return Campaign(
        name="test_sample",
        alias="a",
        state="active",
        layout_supported=True,
        conflict=False,
        is_new=False,
        streams=[geo, offers],
    )


def offers_of(c: Campaign) -> Stream:
    return next(s for s in c.streams if s.role == OFFERS)


def geo_of(c: Campaign) -> Stream:
    return next(s for s in c.streams if s.role == GEO)


def shares(stream: Stream) -> dict[int, int | None]:
    return {o.offer_id: o.draft_share for o in stream.offers if o.draft_active}


def test_add_offer_rebalances_and_is_pending() -> None:
    c = campaign()
    drafts.add_offer(offers_of(c), 603, "Offer 603")

    assert shares(offers_of(c)) == {601: 34, 602: 33, 603: 33}
    assert offer_change(offers_of(c).offers[2]) == "added"
    assert campaign_pending(c)


def test_add_offer_already_active_or_removed_is_refused() -> None:
    c = campaign()
    with pytest.raises(DraftError, match="already in the stream"):
        drafts.add_offer(offers_of(c), 601, "Offer 601")

    drafts.remove_offer(offers_of(c), 601, NOW)
    with pytest.raises(DraftError, match="use Bring back"):
        drafts.add_offer(offers_of(c), 601, "Offer 601")


def test_remove_synced_offer_goes_to_removed() -> None:
    c = campaign()
    drafts.remove_offer(offers_of(c), 602, NOW)

    gone = drafts.find_offer(offers_of(c), 602)
    assert (gone.draft_active, gone.draft_share, gone.removed_by) == (False, None, "adrobot")
    assert offer_change(gone) == "removed"
    assert shares(offers_of(c)) == {601: 100}


def test_remove_offer_added_in_this_draft_drops_it() -> None:
    c = campaign()
    drafts.add_offer(offers_of(c), 603, "Offer 603")
    drafts.remove_offer(offers_of(c), 603, NOW)

    assert [o.offer_id for o in offers_of(c).offers] == [601, 602]
    assert not campaign_pending(c)


def test_bring_back_keeps_the_last_pin() -> None:
    c = campaign()
    drafts.set_pin(offers_of(c), 601, True, 70)
    drafts.remove_offer(offers_of(c), 601, NOW)
    drafts.restore_offer(offers_of(c), 601)

    assert shares(offers_of(c)) == {601: 70, 602: 30}


def test_bring_back_of_an_active_offer_is_refused() -> None:
    with pytest.raises(DraftError, match="isn't removed"):
        drafts.restore_offer(offers_of(campaign()), 601)


def test_pin_and_unpin() -> None:
    c = campaign()
    drafts.add_offer(offers_of(c), 603, "Offer 603")
    drafts.set_pin(offers_of(c), 601, True, 50)
    assert shares(offers_of(c)) == {601: 50, 602: 25, 603: 25}

    drafts.set_pin(offers_of(c), 601, False, None)
    assert shares(offers_of(c)) == {601: 34, 602: 33, 603: 33}


@pytest.mark.parametrize("share", [None, 0, 101])
def test_pin_share_out_of_range_is_refused(share: int | None) -> None:
    with pytest.raises(DraftError, match="1-100%"):
        drafts.set_pin(offers_of(campaign()), 601, True, share)


def test_over_pinned_draft_reports_an_error() -> None:
    c = campaign()
    drafts.set_pin(offers_of(c), 601, True, 70)
    drafts.set_pin(offers_of(c), 602, True, 40)

    assert drafts.share_errors(offers_of(c)) == ["Pinned shares add up to 110%, over 100%"]


def test_geo_is_normalized_and_diffed() -> None:
    c = campaign()
    drafts.set_geo(geo_of(c), [" nz", "AU", "au"])

    assert geo_of(c).draft_geo == ["NZ", "AU"]
    assert geo_changes(geo_of(c)) == (["NZ"], [])
    assert campaign_pending(c)


@pytest.mark.parametrize(("countries", "error"), [([], "at least one"), (["AUS"], "two-letter")])
def test_invalid_geo_is_refused(countries: list[str], error: str) -> None:
    with pytest.raises(DraftError, match=error):
        drafts.set_geo(geo_of(campaign()), countries)


def test_wrong_stream_role_is_refused() -> None:
    c = campaign()
    with pytest.raises(DraftError, match="geo stream, not offers"):
        drafts.add_offer(geo_of(c), 603, "Offer 603")
    with pytest.raises(DraftError, match="offers stream, not geo"):
        drafts.set_geo(offers_of(c), ["AU"])


def test_cancel_restores_synced_and_drops_draft_only_offers() -> None:
    c = campaign()
    c.conflict = True
    drafts.set_geo(geo_of(c), ["NZ"])
    drafts.add_offer(offers_of(c), 603, "Offer 603")
    drafts.remove_offer(offers_of(c), 602, NOW)

    assert drafts.cancel(c) is False

    assert geo_of(c).draft_geo == ["AU"]
    assert [o.offer_id for o in offers_of(c).offers] == [601, 602]
    assert shares(offers_of(c)) == {601: 50, 602: 50}
    assert drafts.find_offer(offers_of(c), 602).removed_by is None
    assert not campaign_pending(c)
    assert not c.conflict


def test_cancel_keeps_offers_removed_in_the_tracker() -> None:
    c = campaign()
    gone = drafts.find_offer(offers_of(c), 602)
    gone.synced_active, gone.synced_share = False, None
    gone.draft_active, gone.draft_share = False, None
    gone.removed_by = "tracker"
    drafts.restore_offer(offers_of(c), 602)

    drafts.cancel(c)

    assert (gone.draft_active, gone.removed_by) == (False, "tracker")


def test_cancel_of_a_new_campaign_asks_to_delete_it() -> None:
    c = campaign()
    c.is_new = True
    assert drafts.cancel(c) is True


@pytest.mark.parametrize(("field", "value"), [("state", ARCHIVED), ("layout_supported", False)])
def test_read_only_campaigns_refuse_edits(field: str, value: object) -> None:
    c = campaign()
    setattr(c, field, value)
    with pytest.raises(DraftError, match="read-only"):
        drafts.ensure_editable(c)
