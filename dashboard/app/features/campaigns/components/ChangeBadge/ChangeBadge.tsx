import { Badge, type BadgeTone } from "@/components/shared/Badge/Badge";

import type { OfferChange } from "../../types";

const LABELS: Record<OfferChange, [string, BadgeTone]> = {
  added: ["added", "info"],
  removed: ["removed", "danger"],
  share: ["share changed", "warning"],
};

export function ChangeBadge({ change }: { change: OfferChange | null }) {
  if (!change) {
    return null;
  }
  const [label, tone] = LABELS[change];
  return <Badge tone={tone}>{label}</Badge>;
}
