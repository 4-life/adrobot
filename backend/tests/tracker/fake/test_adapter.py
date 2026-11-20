from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from app.campaigns import drafts
from app.campaigns.create import OfferPick, new_draft
from app.campaigns.drafts import DraftError
from app.campaigns.merge import apply_campaign_fields, merge_streams
from app.campaigns.pending import campaign_pending
from app.campaigns.push import push, stream_of
from app.campaigns.sync import fetch_one
from app.models.campaign import Campaign
from app.tracker.fake import adapter as fake
from app.tracker.port import OFFERS, OfferShare, TrackerCampaign, TrackerProvider
from tests.fakes import FakeStore

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fresh_state() -> Iterator[None]:
    fake.reset()
    yield
    fake.reset()


def tracker() -> TrackerProvider:
    return fake.InMemoryTracker()


async def test_seed_has_many_offers_some_archived() -> None:
    offers = await tracker().list_offers()

    assert len(offers) == fake.SAMPLE_OFFERS
    assert sum(not o.active for o in offers) == len(fake.ARCHIVED_OFFERS)


async def test_fetch_returns_supported_and_unsupported_campaigns() -> None:
    campaigns = {c.external_id: c for c in await tracker().fetch_campaigns()}

    streams = campaigns[1001].streams
    assert streams is not None
    assert campaigns[1001].group_name == "Sample group"
    assert [o.offer_id for o in streams[1].offers] == [601, 602, 603]
    assert campaigns[1003].streams is None  # one stream only: unsupported layout


async def test_a_new_campaign_is_created_and_read_back() -> None:
    kt = tracker()
    campaign = new_draft(
        name="test_name_campaign9",
        alias="test-name-campaign9-1a2b3c",
        countries=["AU"],
        domain_id=31,
        domain_name=None,
        group_id=None,
        group_name=None,
        traffic_source_id=None,
        traffic_source_name=None,
        offers=[OfferPick(606, "Sample offer 6"), OfferPick(607, "Sample offer 7")],
    )

    result = await push(FakeStore(), kt, campaign, "https://example.com", NOW)

    assert result.mismatch == []
    assert not campaign_pending(campaign)
    assert campaign.external_id is not None
    assert await kt.get_streams(campaign.external_id) is not None


async def test_pushed_offers_are_what_the_next_fetch_sees() -> None:
    kt = tracker()
    seeded = next(c for c in await kt.fetch_campaigns() if c.external_id == 1001)
    assert seeded.streams is not None
    campaign = Campaign(conflict=False, is_new=False, streams=[])
    apply_campaign_fields(campaign, seeded, NOW)
    merge_streams(campaign, seeded.streams, NOW)
    drafts.remove_offer(stream_of(campaign, OFFERS), 603, NOW)

    await push(FakeStore(), kt, campaign, "https://example.com", NOW)

    stored = await kt.get_streams(1001)
    assert stored is not None
    assert [OfferShare(o.offer_id, o.share) for o in stored[1].offers] == [
        OfferShare(601, 50),
        OfferShare(602, 50),
    ]


def synced_seed_campaign(seeded: TrackerCampaign) -> Campaign:
    assert seeded.streams is not None
    campaign = Campaign(conflict=False, is_new=False, streams=[])
    apply_campaign_fields(campaign, seeded, NOW)
    merge_streams(campaign, seeded.streams, NOW)
    return campaign


async def test_fetch_one_picks_up_a_change_made_in_the_tracker() -> None:
    kt = tracker()
    seeded = await kt.fetch_campaign(1001)
    assert seeded is not None
    campaign = synced_seed_campaign(seeded)
    stored = await kt.get_streams(1001)
    assert stored is not None
    await kt.push_offers(stored[1], [OfferShare(601, 70), OfferShare(602, 30)])  # "in Keitaro"

    conflict = await fetch_one(FakeStore(), kt, campaign, NOW)

    assert not conflict
    shares = {o.offer_id: o.draft_share for o in stream_of(campaign, OFFERS).offers}
    assert shares == {601: 70, 602: 30, 603: None}
    removed = drafts.find_offer(stream_of(campaign, OFFERS), 603)
    assert removed.removed_by == "tracker"


async def test_fetch_one_of_a_campaign_gone_from_the_tracker_archives_it() -> None:
    kt = tracker()
    seeded = await kt.fetch_campaign(1001)
    assert seeded is not None
    campaign = synced_seed_campaign(seeded)
    campaign.external_id = 999_999

    await fetch_one(FakeStore(), kt, campaign, NOW)

    assert campaign.state == "archived"


async def test_fetch_one_refuses_a_new_draft() -> None:
    campaign = Campaign(conflict=False, is_new=True, streams=[], external_id=None)
    with pytest.raises(DraftError, match="push it first"):
        await fetch_one(FakeStore(), tracker(), campaign, NOW)
