import type { Offer } from "../../types";

// The draft share; when it differs from the tracker's, the tracker's one struck through.
export function ShareCell({ offer }: { offer: Offer }) {
  const changed = offer.synced_active && offer.draft_share !== offer.synced_share;
  return (
    <span className="tabular-nums">
      {offer.draft_share ?? "–"}%
      {changed && <s className="ml-1.5 text-xs text-muted-foreground">{offer.synced_share}%</s>}
    </span>
  );
}
