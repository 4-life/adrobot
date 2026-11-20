import { Notice } from "@/components/shared/Notice/Notice";

import type { Stream } from "../../types";
import { OfferRow } from "../OfferRow/OfferRow";

// The offers stream's active offers, with why the draft can't be pushed (if it can't).
export function OffersTable({ stream, readOnly }: { stream: Stream; readOnly: boolean }) {
  const active = stream.offers.filter((o) => o.draft_active);

  return (
    <div className="space-y-2">
      {stream.errors.map((error) => (
        <Notice key={error} tone="error">
          {error}
        </Notice>
      ))}
      {active.length === 0 ? (
        <p className="text-sm text-muted-foreground">No active offers.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted-foreground">
            <tr>
              <th className="pb-1 font-normal">Offer</th>
              <th className="pb-1 font-normal">Share</th>
              <th className="pb-1 font-normal">Change</th>
              <th className="pb-1 font-normal">Pin</th>
              <th className="pb-1" />
            </tr>
          </thead>
          <tbody>
            {active.map((offer) => (
              <OfferRow key={offer.id} streamId={stream.id} offer={offer} readOnly={readOnly} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
