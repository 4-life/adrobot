import { useMemo, useState } from "react";

import { type CampaignFilter, DEFAULT_FILTER, filterCampaigns, filterOptions } from "../../filters";
import type { Campaign } from "../../types";
import { CampaignFilters } from "../CampaignFilters/CampaignFilters";
import { CampaignsTable } from "../CampaignsTable/CampaignsTable";

// The campaigns page body: filters, the search starting at CAMPAIGN_NAME_PREFIX (clear it to
// see every campaign), and the table of matching campaigns.
export function CampaignsView({ campaigns, namePrefix }: { campaigns: Campaign[]; namePrefix: string }) {
  const [filter, setFilter] = useState<CampaignFilter>({ ...DEFAULT_FILTER, search: namePrefix });

  const options = useMemo(() => filterOptions(campaigns), [campaigns]);
  const shown = useMemo(() => filterCampaigns(campaigns, filter), [campaigns, filter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CampaignFilters filter={filter} options={options} onChange={setFilter} />
        <span className="text-xs text-muted-foreground">
          {shown.length} of {campaigns.length} campaigns
        </span>
      </div>
      <CampaignsTable campaigns={shown} />
    </div>
  );
}
