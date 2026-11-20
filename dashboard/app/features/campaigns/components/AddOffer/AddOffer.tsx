import type { Stream } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";
import { OfferSearch } from "../OfferSearch/OfferSearch";

// Adds a tracker offer to the offers stream's draft; the shares are rebalanced by the API.
export function AddOffer({ stream }: { stream: Stream }) {
  const action = useCampaignAction();
  // Removed offers come back with Bring back, so they're excluded here too.
  const inStream = stream.offers.map((o) => o.offer_id);

  return (
    <div className="space-y-1">
      <OfferSearch
        excluded={inStream}
        disabled={action.busy}
        onPick={(offer) => action.run("add-offer", { streamId: stream.id, offerId: offer.id })}
      />
    </div>
  );
}
