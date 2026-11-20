import { Notice } from "@/components/shared/Notice/Notice";

import type { Campaign } from "../../types";
import { AddOffer } from "../AddOffer/AddOffer";
import { CampaignActions } from "../CampaignActions/CampaignActions";
import { CampaignBadges } from "../CampaignBadges/CampaignBadges";
import { ConflictBanner } from "../ConflictBanner/ConflictBanner";
import { GeoRow } from "../GeoRow/GeoRow";
import { OffersTable } from "../OffersTable/OffersTable";
import { RemovedOffers } from "../RemovedOffers/RemovedOffers";

function Meta({ campaign }: { campaign: Campaign }) {
  const parts = [
    campaign.external_id ? `#${campaign.external_id}` : "not in the tracker yet",
    `alias ${campaign.alias}`,
    campaign.domain_name,
    campaign.group_name && `group ${campaign.group_name}`,
    campaign.traffic_source_name && `source ${campaign.traffic_source_name}`,
  ].filter(Boolean);
  return <p className="text-xs text-muted-foreground">{parts.join(" · ")}</p>;
}

// One campaign's page body: status, push / cancel, conflict, offers, removed offers, geo.
export function CampaignDetails({ campaign, redirectUrl }: { campaign: Campaign; redirectUrl: string }) {
  const readOnly = campaign.archived || !campaign.layout_supported;
  const geo = campaign.streams.find((s) => s.role === "geo");
  const offers = campaign.streams.find((s) => s.role === "offers");
  const blocked = readOnly || campaign.conflict || (offers?.errors.length ?? 0) > 0;

  return (
    <article className="space-y-4 rounded-lg border bg-card p-4 text-card-foreground">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold">{campaign.name}</h2>
            <CampaignBadges campaign={campaign} />
          </div>
          <Meta campaign={campaign} />
        </div>
        {!readOnly && <CampaignActions campaign={campaign} blocked={blocked} />}
      </header>

      {campaign.conflict && <ConflictBanner campaignId={campaign.id} />}
      {!campaign.layout_supported && (
        <Notice>
          This campaign's streams aren't AdRobot's geo + offers layout, so it's read-only here.
        </Notice>
      )}

      {offers && (
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Offers stream</h3>
          <OffersTable stream={offers} readOnly={readOnly} />
          {!readOnly && <AddOffer stream={offers} />}
          <RemovedOffers stream={offers} readOnly={readOnly} />
        </section>
      )}
      {geo && <GeoRow stream={geo} redirectUrl={redirectUrl} />}
    </article>
  );
}
