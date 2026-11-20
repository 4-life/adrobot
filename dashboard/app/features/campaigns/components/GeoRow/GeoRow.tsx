import { formatCountries } from "../../countries";
import type { Stream } from "../../types";

// The geo stream, read-only: which countries are sent to the redirect. Set when the campaign
// is created; not edited here.
export function GeoRow({ stream, redirectUrl }: { stream: Stream; redirectUrl: string }) {
  return (
    <p className="border-t pt-2 text-xs text-muted-foreground">
      Geo stream: {formatCountries(stream.draft_geo) || "no countries"} → {redirectUrl || "redirect"}
    </p>
  );
}
