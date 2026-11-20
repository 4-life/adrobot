import { ApiStatus } from "@/components/shared/ApiStatus/ApiStatus";
import { Footer } from "@/components/shared/Footer/Footer";
import { Header } from "@/components/shared/Header/Header";
import { Notice } from "@/components/shared/Notice/Notice";
import { runCampaignAction } from "@/features/campaigns/actions.server";
import { campaignDefaults, listCampaigns } from "@/features/campaigns/api.server";
import { CampaignsView } from "@/features/campaigns/components/CampaignsView/CampaignsView";
import { NewCampaignDialog } from "@/features/campaigns/components/NewCampaignDialog/NewCampaignDialog";
import { SyncBar } from "@/features/campaigns/components/SyncBar/SyncBar";
import { lastFetchedAt, pendingCount } from "@/features/campaigns/filters";
import type { Campaign } from "@/features/campaigns/types";
import { ApiError, getHealth } from "@/lib/api.server";

import type { Route } from "./+types/home";

type PageData = {
  healthy: boolean;
  campaigns: Campaign[];
  redirectUrl: string;
  error: string | null;
};

export async function loader(): Promise<PageData> {
  const { healthy } = await getHealth();
  try {
    const [campaigns, defaults] = await Promise.all([listCampaigns(), campaignDefaults()]);
    return { healthy, campaigns, redirectUrl: defaults.redirect_url, error: null };
  } catch (error) {
    if (error instanceof ApiError) {
      return { healthy, campaigns: [], redirectUrl: "", error: error.message };
    }
    throw error;
  }
}

// Every campaign form posts here; the loader then reloads the campaigns.
export async function action({ request }: Route.ActionArgs) {
  return runCampaignAction(await request.formData());
}

export default function Home({ loaderData }: Route.ComponentProps) {
  const { healthy, campaigns, redirectUrl, error } = loaderData;
  return (
    <div className="flex min-h-screen flex-col">
      <Header
        status={<ApiStatus healthy={healthy} />}
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
        <CampaignsView campaigns={campaigns} redirectUrl={redirectUrl} />
      </main>
      <Footer />
    </div>
  );
}
