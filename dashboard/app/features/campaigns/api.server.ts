import { api } from "@/lib/api.server";

import type {
  Campaign,
  CampaignDefaults,
  CancelAllResult,
  CancelResult,
  FetchResult,
  LookupItem,
  NewCampaignInput,
  PushAllResult,
  PushResult,
} from "./types";

// Reading every campaign on a shared tracker, or pushing all of them, takes a while.
const LONG_TIMEOUT_MS = 300_000;

export const listCampaigns = () => api<Campaign[]>("/campaigns?scope=all");

export const fetchStreams = () =>
  api<FetchResult>("/sync/fetch", { method: "POST", timeoutMs: LONG_TIMEOUT_MS });

export const pushCampaign = (campaignId: number) =>
  api<PushResult>(`/campaigns/${campaignId}/push`, { method: "POST" });

export const pushAll = () =>
  api<PushAllResult>("/sync/push-all", { method: "POST", timeoutMs: LONG_TIMEOUT_MS });

export const cancelCampaign = (campaignId: number) =>
  api<CancelResult>(`/campaigns/${campaignId}/cancel`, { method: "POST" });

export const cancelAll = () => api<CancelAllResult>("/sync/cancel-all", { method: "POST" });

export const resolveConflict = (campaignId: number, keepDraft: boolean) =>
  api<CancelResult>(`/campaigns/${campaignId}/resolve`, {
    method: "POST",
    body: { keep_draft: keepDraft },
  });

export const addOffer = (streamId: number, offerId: number) =>
  api<Campaign>(`/streams/${streamId}/offers`, { method: "POST", body: { offer_id: offerId } });

export const setPin = (streamId: number, offerId: number, pinned: boolean, share: number | null) =>
  api<Campaign>(`/streams/${streamId}/offers/${offerId}`, {
    method: "PATCH",
    body: { pinned, pinned_share: share },
  });

export const removeOffer = (streamId: number, offerId: number) =>
  api<Campaign>(`/streams/${streamId}/offers/${offerId}`, { method: "DELETE" });

export const restoreOffer = (streamId: number, offerId: number) =>
  api<Campaign>(`/streams/${streamId}/offers/${offerId}/restore`, { method: "POST" });

export const campaignDefaults = () => api<CampaignDefaults>("/campaigns/defaults");

export const createCampaign = (input: NewCampaignInput) =>
  api<Campaign>("/campaigns", { method: "POST", body: input });

export const searchOffers = (query: string) =>
  api<LookupItem[]>(`/tracker/offers?q=${encodeURIComponent(query)}`);

export const listDomains = () => api<LookupItem[]>("/tracker/domains");
export const listGroups = () => api<LookupItem[]>("/tracker/groups");
export const listSources = () => api<LookupItem[]>("/tracker/sources");
