import { Badge } from "@/components/shared/Badge/Badge";
import { Button } from "@/components/shared/Button/Button";

import type { Offer } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";
import { ChangeBadge } from "../ChangeBadge/ChangeBadge";
import { PinControl } from "../PinControl/PinControl";
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
        {offer.pinned && (
          <span className="ml-1.5">
            <Badge>pinned</Badge>
          </span>
        )}
      </td>
      <td className="py-2 pr-3">
        <ChangeBadge change={offer.change} />
      </td>
      <td className="py-2 pr-3">
        {!readOnly && <PinControl streamId={streamId} offer={offer} disabled={action.busy} />}
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
        {action.error && <div className="text-xs text-red-300">{action.error}</div>}
      </td>
    </tr>
  );
}
