import {
  campaignDefaults,
  listDomains,
  listGroups,
  listSources,
} from "@/features/campaigns/api.server";
import type { NewCampaignData } from "@/features/campaigns/types";
import { ApiError } from "@/lib/api.server";

// Resource route for the New campaign dialog: its defaults and the tracker's selects.
export async function loader(): Promise<NewCampaignData> {
  try {
    const [defaults, domains, groups, sources] = await Promise.all([
      campaignDefaults(),
      listDomains(),
      listGroups(),
      listSources(),
    ]);
    return { ok: true, defaults, domains, groups, sources };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, error: error.message };
    }
    throw error;
  }
}
