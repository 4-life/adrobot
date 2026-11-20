// The AdRobot API's shapes (backend/app/api/schemas.py), written by hand for now.

export type OfferChange = "added" | "removed" | "share";

export type Offer = {
  id: number;
  offer_id: number;
  name: string;
  position: number;
  synced_active: boolean;
  synced_share: number | null;
  draft_active: boolean;
  draft_share: number | null;
  pinned: boolean;
  pinned_share: number | null;
  removed_by: "adrobot" | "tracker" | null;
  removed_at: string | null;
  change: OfferChange | null;
  pending: boolean;
};

export type Stream = {
  id: number;
  external_id: number | null;
  role: "geo" | "offers";
  position: number;
  synced_geo: string[] | null;
  draft_geo: string[] | null;
  geo_added: string[];
  geo_removed: string[];
  offers: Offer[];
  errors: string[];
  pending: boolean;
};

export type Campaign = {
  id: number;
  external_id: number | null;
  name: string;
  alias: string;
  domain_id: number | null;
  domain_name: string | null;
  group_id: number | null;
  group_name: string | null;
  traffic_source_id: number | null;
  traffic_source_name: string | null;
  state: "active" | "disabled" | "archived";
  archived: boolean;
  ours: boolean;
  layout_supported: boolean;
  conflict: boolean;
  is_new: boolean;
  pending: boolean;
  fetched_at: string | null;
  streams: Stream[];
};

export type FetchResult = { fetched_at: string; campaigns: number; conflicts: number[] };
export type LookupItem = { id: number; name: string };
export type CancelResult = { deleted: boolean; campaign: Campaign | null };
export type CancelAllResult = { cancelled: number; deleted: number };
export type PushResult = { pushed: boolean; mismatch: string[]; campaign: Campaign };
export type PushItem = {
  campaign_id: number;
  name: string;
  ok: boolean;
  error: string | null;
  mismatch: string[];
};
export type PushAllResult = { results: PushItem[] };
export type CampaignDefaults = {
  name: string;
  alias: string;
  countries: string[];
  redirect_url: string;
};
export type NewCampaignInput = {
  name: string;
  alias: string;
  countries: string[];
  domain_id: number;
  group_id: number | null;
  traffic_source_id: number | null;
  offer_ids: number[];
};

// The New campaign dialog's data (routes/new-campaign-data.ts).
export type NewCampaignData =
  | {
      ok: true;
      defaults: CampaignDefaults;
      domains: LookupItem[];
      groups: LookupItem[];
      sources: LookupItem[];
    }
  | { ok: false; error: string };

// What every campaign action returns to its form (route action → fetcher.data).
export type ActionResult =
  | { ok: true; message?: string; mismatch?: string[]; pushResults?: PushItem[] }
  | { ok: false; error: string };
