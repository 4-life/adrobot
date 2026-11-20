import { Link } from "react-router";

import { formatCountries } from "../../countries";
import type { Campaign } from "../../types";
import { CampaignBadges } from "../CampaignBadges/CampaignBadges";

const CELL = "py-2 pr-3";

function CampaignRow({ campaign }: { campaign: Campaign }) {
  const geo = campaign.streams.find((s) => s.role === "geo");
  const offers = campaign.streams.find((s) => s.role === "offers");
  const active = offers?.offers.filter((o) => o.draft_active).length ?? 0;

  return (
    <tr className="border-t align-middle hover:bg-accent/40">
      <td className={CELL}>
        <Link to={`/campaigns/${campaign.id}`} className="font-medium hover:underline max-w-[20ch] truncate block" title={campaign.name}>
          {campaign.name}
        </Link>
        <div className="text-xs text-muted-foreground">{campaign.alias}</div>
      </td>
      <td className={CELL}>
        <CampaignBadges campaign={campaign} />
      </td>
      <td className={`${CELL} tabular-nums text-muted-foreground`}>
        {campaign.external_id ? `#${campaign.external_id}` : "–"}
      </td>
      <td className={`${CELL} text-muted-foreground`}>{campaign.domain_name ?? "–"}</td>
      <td className={`${CELL} text-muted-foreground`}>{campaign.group_name ?? "–"}</td>
      <td className={`${CELL} text-muted-foreground`}>{campaign.traffic_source_name ?? "–"}</td>
      <td className={`${CELL} tabular-nums`}>{offers ? active : "–"}</td>
      <td className={`${CELL} text-muted-foreground`}>{geo ? formatCountries(geo.draft_geo) : "–"}</td>
    </tr>
  );
}

// The campaigns list: one row each; the name opens the campaign's page.
export function CampaignsTable({ campaigns }: { campaigns: Campaign[] }) {
  if (campaigns.length === 0) {
    return (
      <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        No campaigns here. Fetch streams, change the filters, or create a new campaign.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
          <tr>
            {["Campaign", "Status", "Tracker id", "Domain", "Group", "Source", "Offers", "Geo"].map(
              (heading) => (
                <th key={heading} className="py-2 pr-3 font-normal first:pl-3">
                  {heading}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody className="[&_td:first-child]:pl-3">
          {campaigns.map((campaign) => (
            <CampaignRow key={campaign.id} campaign={campaign} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
