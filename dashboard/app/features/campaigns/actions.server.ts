import { ApiError } from "@/lib/api.server";

import * as campaignsApi from "./api.server";
import { parseCountries } from "./countries";
import type { ActionResult } from "./types";

// Every campaign form posts an `intent`; the home route's action runs it here.
export async function runCampaignAction(form: FormData): Promise<ActionResult> {
  try {
    return await dispatch(form);
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, error: error.message };
    }
    throw error;
  }
}

async function dispatch(form: FormData): Promise<ActionResult> {
  const intent = text(form, "intent");
  switch (intent) {
    case "fetch": {
      const result = await campaignsApi.fetchStreams();
      const conflicts = result.conflicts.length;
      const suffix = conflicts ? `, ${conflicts} with a conflict` : "";
      return { ok: true, message: `Fetched ${result.campaigns} campaigns${suffix}` };
    }
    case "push": {
      const result = await campaignsApi.pushCampaign(id(form, "campaignId"));
      const message = result.pushed ? "Pushed to the tracker" : "Nothing to push";
      return { ok: true, message, mismatch: result.mismatch };
    }
    case "push-all": {
      const { results } = await campaignsApi.pushAll();
      const pushed = results.filter((item) => item.ok).length;
      return { ok: true, message: `Pushed ${pushed} of ${results.length}`, pushResults: results };
    }
    case "cancel": {
      const result = await campaignsApi.cancelCampaign(id(form, "campaignId"));
      return { ok: true, message: result.deleted ? "Draft deleted" : "Changes cancelled" };
    }
    case "cancel-all": {
      const result = await campaignsApi.cancelAll();
      return {
        ok: true,
        message: `Cancelled ${result.cancelled}, deleted ${result.deleted} new drafts`,
      };
    }
    case "resolve": {
      const keepDraft = text(form, "keepDraft") === "true";
      await campaignsApi.resolveConflict(id(form, "campaignId"), keepDraft);
      return { ok: true, message: keepDraft ? "Draft kept: push it" : "Draft cancelled" };
    }
    case "set-geo": {
      await campaignsApi.setGeo(id(form, "streamId"), parseCountries(text(form, "countries")));
      return { ok: true };
    }
    case "add-offer": {
      await campaignsApi.addOffer(id(form, "streamId"), id(form, "offerId"));
      return { ok: true };
    }
    case "pin": {
      const pinned = text(form, "pinned") === "true";
      const share = pinned ? Number(text(form, "pinnedShare")) : null;
      await campaignsApi.setPin(id(form, "streamId"), id(form, "offerId"), pinned, share);
      return { ok: true };
    }
    case "remove-offer": {
      await campaignsApi.removeOffer(id(form, "streamId"), id(form, "offerId"));
      return { ok: true };
    }
    case "restore-offer": {
      await campaignsApi.restoreOffer(id(form, "streamId"), id(form, "offerId"));
      return { ok: true };
    }
    case "create": {
      await campaignsApi.createCampaign({
        name: text(form, "name"),
        alias: text(form, "alias"),
        countries: parseCountries(text(form, "countries")),
        domain_id: id(form, "domainId"),
        group_id: optionalId(form, "groupId"),
        traffic_source_id: optionalId(form, "sourceId"),
        offer_ids: form.getAll("offerIds").map(Number),
      });
      return { ok: true, message: "Draft created: push it to create it in the tracker" };
    }
    default:
      return { ok: false, error: `Unknown action: ${intent || "none"}` };
  }
}

function text(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function optionalId(form: FormData, name: string): number | null {
  return text(form, name) ? id(form, name) : null;
}

function id(form: FormData, name: string): number {
  const value = Number(text(form, name));
  if (!Number.isInteger(value) || value <= 0) {
    throw new ApiError(422, `Missing ${name}`);
  }
  return value;
}
