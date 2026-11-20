import type { Campaign } from "../../types";
import { CampaignCard } from "../CampaignCard/CampaignCard";

export function CampaignList({ campaigns, redirectUrl }: { campaigns: Campaign[]; redirectUrl: string }) {
  if (campaigns.length === 0) {
    return (
      <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        No campaigns here. Fetch streams, change the filters, or create a new campaign.
      </p>
    );
  }
  return (
    <div className="space-y-4">
      {campaigns.map((campaign) => (
        <CampaignCard key={campaign.id} campaign={campaign} redirectUrl={redirectUrl} />
      ))}
    </div>
  );
}
