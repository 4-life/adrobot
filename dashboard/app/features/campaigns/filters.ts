import type { Campaign, LookupItem } from "./types";

export type CampaignFilter = {
  search: string; // name or alias contains it (CAMPAIGN_NAME_PREFIX by default)
  pendingOnly: boolean;
  groupId: number | null;
  domainId: number | null;
  sourceId: number | null;
};

export const DEFAULT_FILTER: CampaignFilter = {
  search: "",
  pendingOnly: false,
  groupId: null,
  domainId: null,
  sourceId: null,
};

export function filterCampaigns(campaigns: Campaign[], filter: CampaignFilter): Campaign[] {
  const needle = filter.search.trim().toLowerCase();
  return campaigns.filter(
    (c) =>
      (!filter.pendingOnly || c.pending) &&
      (filter.groupId === null || c.group_id === filter.groupId) &&
      (filter.domainId === null || c.domain_id === filter.domainId) &&
      (filter.sourceId === null || c.traffic_source_id === filter.sourceId) &&
      (!needle || c.name.toLowerCase().includes(needle) || c.alias.toLowerCase().includes(needle)),
  );
}

export type FilterOptions = { groups: LookupItem[]; domains: LookupItem[]; sources: LookupItem[] };

// The groups, domains and sources the campaigns have, for the filter selects.
export function filterOptions(campaigns: Campaign[]): FilterOptions {
  return {
    groups: distinct(campaigns.map((c) => [c.group_id, c.group_name])),
    domains: distinct(campaigns.map((c) => [c.domain_id, c.domain_name])),
    sources: distinct(campaigns.map((c) => [c.traffic_source_id, c.traffic_source_name])),
  };
}

function distinct(pairs: [number | null, string | null][]): LookupItem[] {
  const byId = new Map<number, string>();
  for (const [itemId, name] of pairs) {
    if (itemId !== null) {
      byId.set(itemId, name ?? `#${itemId}`);
    }
  }
  return [...byId]
    .map(([itemId, name]) => ({ id: itemId, name }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function pendingCount(campaigns: Campaign[]): number {
  return campaigns.filter((c) => c.pending).length;
}

export function lastFetchedAt(campaigns: Campaign[]): string | null {
  const times = campaigns.map((c) => c.fetched_at).filter((t): t is string => t !== null);
  return times.length ? times.reduce((a, b) => (a > b ? a : b)) : null;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
