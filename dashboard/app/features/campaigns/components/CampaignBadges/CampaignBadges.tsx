import { Badge } from "@/components/shared/Badge/Badge";

import type { Campaign } from "../../types";

export function CampaignBadges({ campaign }: { campaign: Campaign }) {
  return (
    <span className="flex flex-wrap gap-1">
      {campaign.is_new && <Badge tone="info">New, not in the tracker</Badge>}
      {campaign.pending && !campaign.is_new && <Badge tone="warning">Not synced</Badge>}
      {campaign.conflict && <Badge tone="danger">Conflict</Badge>}
      {campaign.archived && <Badge>Archived in the tracker</Badge>}
      {!campaign.layout_supported && <Badge>Unsupported layout</Badge>}
      {campaign.state === "disabled" && <Badge>Disabled</Badge>}
    </span>
  );
}
