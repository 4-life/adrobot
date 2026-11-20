import { useEffect, useMemo, useState } from "react";

import { type CampaignFilter, DEFAULT_FILTER, filterCampaigns, filterOptions, type Scope } from "../../filters";
import type { Campaign } from "../../types";
import { CampaignFilters } from "../CampaignFilters/CampaignFilters";
import { CampaignsTable } from "../CampaignsTable/CampaignsTable";

const SCOPE_KEY = "adrobot.scope"; // the Ours / All choice, remembered in this browser

function storedScope(): Scope | null {
  try {
    const value = window.localStorage.getItem(SCOPE_KEY);
    return value === "ours" || value === "all" ? value : null;
  } catch {
    return null;
  }
}

// The campaigns page body: filters (Ours by default) and the table of matching campaigns.
export function CampaignsView({ campaigns }: { campaigns: Campaign[] }) {
  const [filter, setFilter] = useState<CampaignFilter>(DEFAULT_FILTER);

  useEffect(() => {
    const scope = storedScope();
    if (scope) {
      setFilter((current) => ({ ...current, scope }));
    }
  }, []);

  const change = (next: CampaignFilter) => {
    setFilter(next);
    try {
      window.localStorage.setItem(SCOPE_KEY, next.scope);
    } catch {
      // storage unavailable: the choice just isn't remembered
    }
  };

  const options = useMemo(() => filterOptions(campaigns), [campaigns]);
  const shown = useMemo(() => filterCampaigns(campaigns, filter), [campaigns, filter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CampaignFilters filter={filter} options={options} onChange={change} />
        <span className="text-xs text-muted-foreground">
          {shown.length} of {campaigns.length} campaigns
        </span>
      </div>
      <CampaignsTable campaigns={shown} />
    </div>
  );
}
