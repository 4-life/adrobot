import { useState } from "react";

import { Button } from "@/components/shared/Button/Button";
import { TextInput } from "@/components/shared/Field/Field";

import type { Offer } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";

// Pin an offer's share (1-100 %) so it stays fixed however many offers are added.
export function PinControl({
  streamId,
  offer,
  disabled,
}: {
  streamId: number;
  offer: Offer;
  disabled: boolean;
}) {
  const action = useCampaignAction();
  const [share, setShare] = useState(String(offer.pinned_share ?? offer.draft_share ?? ""));

  const pin = (pinned: boolean) =>
    action.run("pin", {
      streamId,
      offerId: offer.offer_id,
      pinned,
      pinnedShare: pinned ? share : null,
    });

  return (
    <div className="flex items-center gap-1.5">
      <TextInput
        aria-label={`Pinned share of ${offer.name}`}
        type="number"
        min={1}
        max={100}
        value={share}
        disabled={disabled || action.busy}
        onChange={(event) => setShare(event.target.value)}
        className="h-7 w-16 px-1.5 text-xs"
      />
      {offer.pinned ? (
        <>
          <Button size="sm" disabled={disabled || action.busy} onClick={() => pin(true)}>
            Update
          </Button>
          <Button size="sm" variant="ghost" disabled={disabled || action.busy} onClick={() => pin(false)}>
            Unpin
          </Button>
        </>
      ) : (
        <Button size="sm" disabled={disabled || action.busy} onClick={() => pin(true)}>
          Pin
        </Button>
      )}
      {action.error && <span className="text-xs text-red-300">{action.error}</span>}
    </div>
  );
}
