from datetime import UTC, datetime

import pytest

from app.campaigns import drafts
from app.campaigns.create import OfferPick, new_draft
from app.campaigns.drafts import DraftError
from app.campaigns.merge import merge_streams
from app.campaigns.pending import campaign_pending
from app.campaigns.push import push, stream_of
from app.models.campaign import Campaign
from app.tracker.port import GEO, OFFERS, OfferShare, TrackerError
from tests.fakes import FakeStore, FakeTracker

NOW = datetime(2026, 1, 1, tzinfo=UTC)
REDIRECT = "https://example.com"


def new_campaign() -> Campaign:
    return new_draft(
        name="test_name_campaign1",
        alias="test-name-campaign1-1a2b3c",
        countries=["AU"],
        domain_id=31,
        domain_name=None,
        group_id=None,
        group_name=None,
        traffic_source_id=None,
        traffic_source_name=None,
        offers=[OfferPick(601, "Offer 601"), OfferPick(602, "Offer 602")],
    )


def synced_campaign(tracker: FakeTracker) -> Campaign:
    """A campaign already in the tracker, merged from its current streams."""
    campaign = Campaign(
        external_id=tracker.campaign_id,
        name="test_name_campaign1",
        alias="a",
        state="active",
        layout_supported=True,
        conflict=False,
        is_new=False,
    )
    merge_streams(campaign, tracker.streams(), NOW)
    return campaign


def existing() -> tuple[FakeTracker, Campaign]:
    tracker = FakeTracker(offers=[OfferShare(601, 50), OfferShare(602, 50)])
    return tracker, synced_campaign(tracker)


async def test_new_campaign_is_created_step_by_step() -> None:
    tracker, campaign = FakeTracker(), new_campaign()

    result = await push(FakeStore(), tracker, campaign, REDIRECT, NOW)

    assert result.pushed and result.mismatch == []
    assert tracker.calls == [
        "create_campaign",
        "create_geo_stream",
        "create_offers_stream",
        "get_streams",
    ]
    assert tracker.offers == [OfferShare(601, 50), OfferShare(602, 50)]
    assert campaign.external_id == 1001
    assert [s.external_id for s in campaign.streams] == [501, 502]
    assert not campaign.is_new
    assert not campaign_pending(campaign)


async def test_failed_create_resumes_from_the_failed_step() -> None:
    tracker, campaign = FakeTracker(fail_on="create_offers_stream"), new_campaign()
    with pytest.raises(TrackerError):
        await push(FakeStore(), tracker, campaign, REDIRECT, NOW)
    assert (campaign.external_id, stream_of(campaign, GEO).external_id) == (1001, 501)
    assert stream_of(campaign, OFFERS).external_id is None
    assert campaign.is_new

    tracker.calls.clear()
    await push(FakeStore(), tracker, campaign, REDIRECT, NOW)

    assert tracker.calls == ["create_offers_stream", "get_streams"]
    assert not campaign.is_new


async def test_changed_offers_are_pushed_and_synced() -> None:
    tracker, campaign = existing()
    drafts.remove_offer(stream_of(campaign, OFFERS), 602, NOW)

    result = await push(FakeStore(), tracker, campaign, REDIRECT, NOW)

    assert result.pushed and result.mismatch == []
    assert tracker.calls == ["get_streams", "push_offers", "get_streams"]
    assert tracker.offers == [OfferShare(601, 100)]
    removed = drafts.find_offer(stream_of(campaign, OFFERS), 602)
    assert (removed.draft_active, removed.removed_by) == (False, "adrobot")
    assert not campaign_pending(campaign)


async def test_only_the_changed_stream_is_pushed() -> None:
    tracker, campaign = existing()
    drafts.set_geo(stream_of(campaign, GEO), ["NZ"])

    await push(FakeStore(), tracker, campaign, REDIRECT, NOW)

    assert tracker.calls == ["get_streams", "push_geo", "get_streams"]
    assert tracker.geo == ["NZ"]


async def test_tracker_changed_since_fetch_is_a_conflict() -> None:
    tracker, campaign = existing()
    drafts.set_pin(stream_of(campaign, OFFERS), 601, True, 80)
    tracker.offers = [OfferShare(601, 70), OfferShare(602, 30)]  # edited in the tracker

    with pytest.raises(DraftError, match="changed since the last fetch"):
        await push(FakeStore(), tracker, campaign, REDIRECT, NOW)

    assert campaign.conflict
    assert tracker.calls == ["get_streams"]
    assert drafts.find_offer(stream_of(campaign, OFFERS), 601).synced_share == 70
    assert drafts.find_offer(stream_of(campaign, OFFERS), 601).draft_share == 80


async def test_conflicted_campaign_is_refused_until_resolved() -> None:
    tracker, campaign = existing()
    drafts.set_geo(stream_of(campaign, GEO), ["NZ"])
    campaign.conflict = True

    with pytest.raises(DraftError, match="keep the draft or cancel"):
        await push(FakeStore(), tracker, campaign, REDIRECT, NOW)
    assert tracker.calls == []

    campaign.conflict = False  # resolved: keep the draft
    await push(FakeStore(), tracker, campaign, REDIRECT, NOW)
    assert tracker.geo == ["NZ"]


async def test_invalid_draft_is_refused() -> None:
    tracker, campaign = existing()
    drafts.set_pin(stream_of(campaign, OFFERS), 601, True, 70)
    drafts.set_pin(stream_of(campaign, OFFERS), 602, True, 40)

    with pytest.raises(DraftError, match="over 100%"):
        await push(FakeStore(), tracker, campaign, REDIRECT, NOW)
    assert tracker.calls == []


async def test_nothing_pending_pushes_nothing() -> None:
    tracker, campaign = existing()

    result = await push(FakeStore(), tracker, campaign, REDIRECT, NOW)

    assert not result.pushed
    assert tracker.calls == []


async def test_tracker_storing_something_else_is_reported_and_followed() -> None:
    tracker, campaign = existing()
    tracker.keep_removed = True  # a tracker that merges offers instead of replacing them
    drafts.remove_offer(stream_of(campaign, OFFERS), 602, NOW)

    result = await push(FakeStore(), tracker, campaign, REDIRECT, NOW)

    assert result.mismatch and result.mismatch[0].startswith("Offers: sent")
    assert drafts.find_offer(stream_of(campaign, OFFERS), 602).synced_active
    assert not campaign_pending(campaign)


async def test_every_step_is_logged() -> None:
    store, tracker, campaign = FakeStore(), FakeTracker(), new_campaign()

    await push(store, tracker, campaign, REDIRECT, NOW)

    steps = [getattr(entry, "step", None) for entry in store.added]
    assert steps == ["create campaign", "create geo stream", "create offers stream", "done"]
