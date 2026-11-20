from datetime import UTC, datetime

from app.campaigns.merge import merge_streams
from app.campaigns.pending import campaign_pending
from app.models.campaign import Campaign, Stream, StreamOffer
from app.tracker.port import GEO, OFFERS, TrackerOffer, TrackerStream

NOW = datetime(2026, 1, 1, tzinfo=UTC)
NAMES = {601: "Offer A", 602: "Offer B", 603: "Offer C"}


def fetched(geo: list[str], offers: list[tuple[int, int]]) -> list[TrackerStream]:
    return [
        TrackerStream(external_id=501, role=GEO, position=1, geo=geo, offers=[], raw={"id": 501}),
        TrackerStream(
            external_id=502,
            role=OFFERS,
            position=2,
            geo=None,
            offers=[TrackerOffer(offer_id, NAMES[offer_id], share) for offer_id, share in offers],
            raw={"id": 502},
        ),
    ]


def new_campaign() -> Campaign:
    return Campaign(name="test_sample", alias="a", conflict=False, is_new=False)


def offers_of(campaign: Campaign) -> Stream:
    return next(s for s in campaign.streams if s.role == OFFERS)


def geo_of(campaign: Campaign) -> Stream:
    return next(s for s in campaign.streams if s.role == GEO)


def offer(campaign: Campaign, offer_id: int) -> StreamOffer:
    return next(o for o in offers_of(campaign).offers if o.offer_id == offer_id)


def synced(campaign: Campaign) -> Campaign:
    merge_streams(campaign, fetched(["AU"], [(601, 50), (602, 50)]), NOW)
    return campaign


def test_first_fetch_creates_both_streams_in_sync() -> None:
    campaign = synced(new_campaign())

    assert geo_of(campaign).synced_geo == geo_of(campaign).draft_geo == ["AU"]
    rows = [(o.offer_id, o.name, o.position, o.draft_share) for o in offers_of(campaign).offers]
    assert rows == [(601, "Offer A", 0, 50), (602, "Offer B", 1, 50)]
    assert not campaign_pending(campaign)
    assert not campaign.conflict


def test_offer_removed_in_tracker_moves_to_removed() -> None:
    campaign = synced(new_campaign())

    conflict = merge_streams(campaign, fetched(["AU"], [(601, 100)]), NOW)

    gone = offer(campaign, 602)
    assert not conflict
    assert (gone.synced_active, gone.draft_active) == (False, False)
    assert (gone.removed_by, gone.removed_at) == ("tracker", NOW)
    assert offer(campaign, 601).draft_share == 100
    assert not campaign_pending(campaign)


def test_offer_added_in_tracker_is_appended() -> None:
    campaign = synced(new_campaign())

    merge_streams(campaign, fetched(["AU"], [(601, 50), (602, 25), (603, 25)]), NOW)

    added = offer(campaign, 603)
    assert (added.position, added.draft_active, added.draft_share) == (2, True, 25)


def test_pending_draft_without_tracker_change_is_kept() -> None:
    campaign = synced(new_campaign())
    offer(campaign, 601).draft_share = 70
    offer(campaign, 602).draft_share = 30

    conflict = merge_streams(campaign, fetched(["AU"], [(601, 50), (602, 50)]), NOW)

    assert not conflict
    assert offer(campaign, 601).draft_share == 70
    assert campaign_pending(campaign)


def test_pending_draft_with_tracker_change_is_a_conflict() -> None:
    campaign = synced(new_campaign())
    offer(campaign, 601).draft_share = 70
    offer(campaign, 602).draft_share = 30

    conflict = merge_streams(campaign, fetched(["AU"], [(601, 40), (602, 60)]), NOW)

    assert conflict and campaign.conflict
    assert offer(campaign, 601).synced_share == 40
    assert offer(campaign, 601).draft_share == 70


def test_conflict_stays_flagged_on_the_next_fetch() -> None:
    campaign = synced(new_campaign())
    offer(campaign, 601).draft_share = 70
    offer(campaign, 602).draft_share = 30
    merge_streams(campaign, fetched(["AU"], [(601, 40), (602, 60)]), NOW)

    merge_streams(campaign, fetched(["AU"], [(601, 40), (602, 60)]), NOW)

    assert campaign.conflict


def test_conflict_clears_once_nothing_is_pending() -> None:
    campaign = synced(new_campaign())
    offer(campaign, 601).draft_share = 70
    offer(campaign, 602).draft_share = 30
    merge_streams(campaign, fetched(["AU"], [(601, 40), (602, 60)]), NOW)
    offer(campaign, 601).draft_share = 40  # cancelled by hand back to synced
    offer(campaign, 602).draft_share = 60

    merge_streams(campaign, fetched(["AU"], [(601, 40), (602, 60)]), NOW)

    assert not campaign.conflict


def test_geo_change_in_tracker_follows_without_pending() -> None:
    campaign = synced(new_campaign())

    merge_streams(campaign, fetched(["AU", "NZ"], [(601, 50), (602, 50)]), NOW)

    assert geo_of(campaign).draft_geo == ["AU", "NZ"]
    assert not campaign.conflict


def test_pending_geo_with_tracker_change_is_a_conflict() -> None:
    campaign = synced(new_campaign())
    geo_of(campaign).draft_geo = ["AU", "GB"]

    conflict = merge_streams(campaign, fetched(["NZ"], [(601, 50), (602, 50)]), NOW)

    assert conflict
    assert geo_of(campaign).synced_geo == ["NZ"]
    assert geo_of(campaign).draft_geo == ["AU", "GB"]


def test_removed_offer_reappearing_in_tracker_comes_back() -> None:
    campaign = synced(new_campaign())
    merge_streams(campaign, fetched(["AU"], [(601, 100)]), NOW)

    merge_streams(campaign, fetched(["AU"], [(601, 50), (602, 50)]), NOW)

    back = offer(campaign, 602)
    assert (back.draft_active, back.removed_by) == (True, None)
