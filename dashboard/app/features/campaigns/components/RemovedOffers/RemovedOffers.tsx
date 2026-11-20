import { Button } from "@/components/shared/Button/Button";

import { formatTime } from "../../filters";
import type { Offer, Stream } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";
import { ChangeBadge } from "../ChangeBadge/ChangeBadge";

function RemovedRow({ streamId, offer, readOnly }: { streamId: number; offer: Offer; readOnly: boolean }) {
  const action = useCampaignAction();
  const by = offer.removed_by === "tracker" ? "in the tracker" : "in AdRobot";

  return (
    <li className="flex items-center justify-between gap-3 py-1.5 text-sm">
      <span>
        {offer.name} <span className="text-xs text-muted-foreground">#{offer.offer_id}</span>
        <span className="ml-2 text-xs text-muted-foreground">
          removed {by}
          {offer.removed_at && `, ${formatTime(offer.removed_at)}`}
        </span>
        <span className="ml-2">
          <ChangeBadge change={offer.change} />
        </span>
      </span>
      {!readOnly && (
        <Button
          size="sm"
          disabled={action.busy}
          onClick={() => action.run("restore-offer", { streamId, offerId: offer.offer_id })}
        >
          Bring back
        </Button>
      )}
      {action.error && <span className="text-xs text-red-300">{action.error}</span>}
    </li>
  );
}

// Offers removed in AdRobot or in the tracker: kept for this campaign, each can be brought back.
export function RemovedOffers({ stream, readOnly }: { stream: Stream; readOnly: boolean }) {
  const removed = stream.offers.filter((o) => !o.draft_active);
  if (removed.length === 0) {
    return null;
  }
  return (
    <details className="rounded-md border px-3 py-2">
      <summary className="cursor-pointer text-sm text-muted-foreground">Removed ({removed.length})</summary>
      <ul className="divide-y">
        {removed.map((offer) => (
          <RemovedRow key={offer.id} streamId={stream.id} offer={offer} readOnly={readOnly} />
        ))}
      </ul>
    </details>
  );
}
