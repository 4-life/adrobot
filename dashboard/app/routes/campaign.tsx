import { Link, data, isRouteErrorResponse, useRouteError } from "react-router";

import { Footer } from "@/components/shared/Footer/Footer";
import { Header } from "@/components/shared/Header/Header";
import { campaignDefaults, getCampaign } from "@/features/campaigns/api.server";
import { CampaignDetails } from "@/features/campaigns/components/CampaignDetails/CampaignDetails";
import { ApiError } from "@/lib/api.server";

import type { Route } from "./+types/campaign";

export async function loader({ params }: Route.LoaderArgs) {
  const campaignId = Number(params.id);
  if (!Number.isInteger(campaignId) || campaignId <= 0) {
    throw data("Campaign not found", { status: 404 });
  }
  try {
    const [campaign, defaults] = await Promise.all([getCampaign(campaignId), campaignDefaults()]);
    return { campaign, redirectUrl: defaults.redirect_url };
  } catch (error) {
    if (error instanceof ApiError) {
      throw data(error.message, { status: error.status || 502 });
    }
    throw error;
  }
}

export function meta({ data: loaded }: Route.MetaArgs) {
  return [{ title: loaded ? `${loaded.campaign.name} · AdRobot` : "AdRobot" }];
}

function BackLink() {
  return (
    <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
      ← Campaigns
    </Link>
  );
}

export default function CampaignPage({ loaderData }: Route.ComponentProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header actions={<BackLink />} />
      <main className="mx-auto w-full max-w-6xl flex-1 p-4">
        <CampaignDetails campaign={loaderData.campaign} redirectUrl={loaderData.redirectUrl} />
      </main>
      <Footer />
    </div>
  );
}

export function ErrorBoundary() {
  const error = useRouteError();
  const message = isRouteErrorResponse(error) ? String(error.data) : "Something went wrong";
  return (
    <div className="flex min-h-screen flex-col">
      <Header actions={<BackLink />} />
      <main className="mx-auto w-full max-w-6xl flex-1 p-4 text-sm text-muted-foreground">
        {message}
      </main>
      <Footer />
    </div>
  );
}
