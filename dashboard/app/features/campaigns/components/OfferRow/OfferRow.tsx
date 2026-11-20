import { Button } from "@/components/shared/Button/Button";
import { PinIcon } from "@/components/shared/PinIcon/PinIcon";

import type { Offer } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";
import { ChangeBadge } from "../ChangeBadge/ChangeBadge";
import { PinToggle } from "../PinToggle/PinToggle";
import { ShareCell } from "../ShareCell/ShareCell";

export function OfferRow({
  streamId,
  offer,
  readOnly,
}: {
  streamId: number;
  offer: Offer;
  readOnly: boolean;
}) {
  const action = useCampaignAction();

  return (
    <tr className="border-t align-middle">
      <td className="py-2 pr-3">
        <div className="font-medium">{offer.name}</div>
        <div className="text-xs text-muted-foreground">#{offer.offer_id}</div>
      </td>
      <td className="py-2 pr-3">
        <ShareCell offer={offer} />
        {readOnly ? (
          offer.pinned && (
            <span className="ml-1.5 inline-flex align-middle text-amber-300" title="Pinned">
              <PinIcon filled />
            </span>
          )
        ) : (
          <PinToggle streamId={streamId} offer={offer} />
        )}
      </td>
      <td className="py-2 pr-3">
        <ChangeBadge change={offer.change} />
      </td>
      <td className="py-2 text-right">
        {!readOnly && (
          <Button
            size="sm"
            variant="ghost"
            disabled={action.busy}
            onClick={() => action.run("remove-offer", { streamId, offerId: offer.offer_id })}
          >
            Remove
          </Button>
        )}
      </td>
    </tr>
  );
}
