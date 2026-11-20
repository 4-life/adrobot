"""Fetch streams: reads every tracker campaign with its streams and merges it into Postgres.

Depends only on the tracker port; the adapter is injected.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.campaigns.merge import apply_campaign_fields, merge_streams
from app.models.campaign import ARCHIVED, Campaign, Stream, SyncLog
from app.tracker.port import TrackerProvider


@dataclass(frozen=True)
class FetchResult:
    fetched_at: datetime
    campaigns: int
    conflicts: list[int]  # AdRobot campaign ids flagged Conflict


async def fetch_all(session: AsyncSession, tracker: TrackerProvider) -> FetchResult:
    now = datetime.now(UTC)
    tracked_campaigns = await tracker.fetch_campaigns()

    loaded = await session.scalars(
        select(Campaign)
        .where(Campaign.external_id.is_not(None))
        .options(selectinload(Campaign.streams).selectinload(Stream.offers))
    )
    local = {c.external_id: c for c in loaded}

    seen: set[int] = set()
    conflicts: list[Campaign] = []
    for tracked in tracked_campaigns:
        seen.add(tracked.external_id)
        campaign = local.get(tracked.external_id)
        if campaign is None:
            campaign = Campaign(conflict=False, is_new=False, streams=[])  # no lazy loads later
            session.add(campaign)
        apply_campaign_fields(campaign, tracked, now)
        if tracked.streams is not None and merge_streams(campaign, tracked.streams, now):
            conflicts.append(campaign)

    for external_id, campaign in local.items():
        if external_id not in seen:
            campaign.state = ARCHIVED

    summary = f"{len(seen)} campaigns, {len(conflicts)} conflicts"
    session.add(SyncLog(action="fetch", ok=True, summary=summary))
    await session.commit()
    return FetchResult(fetched_at=now, campaigns=len(seen), conflicts=[c.id for c in conflicts])
