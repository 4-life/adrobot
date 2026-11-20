import { Button } from "@/components/shared/Button/Button";
import { Spinner } from "@/components/shared/Spinner/Spinner";

import { formatTime } from "../../filters";
import type { Campaign } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";

// Re-reads this one campaign from Keitaro (after a change made there): fast, unlike the full
// Fetch streams. A pending draft is kept; a change under it shows as a conflict.
export function FetchCampaignButton({ campaign }: { campaign: Campaign }) {
  const action = useCampaignAction();

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-end gap-2">
        {action.busy && <Spinner label="Fetching" />}
        {campaign.fetched_at && (
          <span className="text-xs text-muted-foreground">
            Fetched {formatTime(campaign.fetched_at)}
          </span>
        )}
        <Button
          size="sm"
          disabled={action.busy}
          onClick={() => action.run("fetch-one", { campaignId: campaign.id })}
        >
          Fetch from Keitaro
        </Button>
      </div>
    </div>
  );
}
