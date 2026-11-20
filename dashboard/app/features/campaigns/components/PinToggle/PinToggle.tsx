import { PinIcon } from "@/components/shared/PinIcon/PinIcon";
import { cn } from "@/lib/utils";

import type { Offer } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";

// Pins the offer at its current share (it then stays fixed however many offers are added),
// or unpins it.
export function PinToggle({ streamId, offer }: { streamId: number; offer: Offer }) {
  const action = useCampaignAction();
  const { pinned } = offer;
  const label = pinned ? `Unpin (pinned at ${offer.pinned_share}%)` : `Pin at ${offer.draft_share}%`;

  return (
    <>
      <button
        type="button"
        aria-pressed={pinned}
        aria-label={label}
        title={label}
        disabled={action.busy || offer.draft_share === null}
        onClick={() =>
          action.run("pin", {
            streamId,
            offerId: offer.offer_id,
            pinned: !pinned,
            pinnedShare: pinned ? null : offer.draft_share,
          })
        }
        className={cn(
          "ml-1.5 inline-flex rounded p-0.5 align-middle disabled:cursor-not-allowed",
          pinned ? "text-amber-300" : "text-muted-foreground opacity-40 hover:opacity-100",
        )}
      >
        <PinIcon filled={pinned} />
      </button>
      {action.error && <span className="ml-1.5 text-xs text-red-300">{action.error}</span>}
    </>
  );
}
