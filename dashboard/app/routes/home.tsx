import { Footer } from "@/components/shared/Footer/Footer";
import { Header } from "@/components/shared/Header/Header";
import { Notice } from "@/components/shared/Notice/Notice";
import { campaignDefaults, listCampaigns } from "@/features/campaigns/api.server";
import { CampaignsView } from "@/features/campaigns/components/CampaignsView/CampaignsView";
import { NewCampaignDialog } from "@/features/campaigns/components/NewCampaignDialog/NewCampaignDialog";
import { SyncBar } from "@/features/campaigns/components/SyncBar/SyncBar";
import { lastFetchedAt, pendingCount } from "@/features/campaigns/filters";
import type { Campaign } from "@/features/campaigns/types";
import { ApiError } from "@/lib/api.server";

import type { Route } from "./+types/home";

type PageData = {
  campaigns: Campaign[];
  namePrefix: string; // CAMPAIGN_NAME_PREFIX: the search box starts with it
  error: string | null; // the API's error (or "unreachable"), shown above the table
};

export async function loader(): Promise<PageData> {
  try {
    const [campaigns, defaults] = await Promise.all([listCampaigns(), campaignDefaults()]);
    return { campaigns, namePrefix: defaults.name_prefix, error: null };
  } catch (error) {
    if (error instanceof ApiError) {
      return { campaigns: [], namePrefix: "", error: error.message };
    }
    throw error;
  }
}

// The campaigns table; a campaign opens on its own page (routes/campaign.tsx).
export default function Home({ loaderData }: Route.ComponentProps) {
  const { campaigns, namePrefix, error } = loaderData;
  return (
    <div className="flex min-h-screen flex-col">
      <Header
        actions={
          <SyncBar
            pending={pendingCount(campaigns)}
            lastFetched={lastFetchedAt(campaigns)}
            newCampaign={<NewCampaignDialog />}
          />
        }
      />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-4 p-4">
        {error && <Notice tone="error">{error}</Notice>}
        <CampaignsView campaigns={campaigns} namePrefix={namePrefix} />
      </main>
      <Footer />
    </div>
  );
}
