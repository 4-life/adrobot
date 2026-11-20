import { searchOffers } from "@/features/campaigns/api.server";
import type { LookupItem } from "@/features/campaigns/types";
import { ApiError } from "@/lib/api.server";

import type { Route } from "./+types/offers-search";

// Resource route for OfferSearch: the tracker's active offers matching ?q= (name or id).
export async function loader({ request }: Route.LoaderArgs): Promise<LookupItem[]> {
  const query = new URL(request.url).searchParams.get("q") ?? "";
  try {
    return await searchOffers(query);
  } catch (error) {
    if (error instanceof ApiError) {
      return [];
    }
    throw error;
  }
}
