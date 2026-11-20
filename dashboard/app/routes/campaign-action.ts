import { runCampaignAction } from "@/features/campaigns/actions.server";

import type { Route } from "./+types/campaign-action";

// Resource route: every campaign form posts here (useCampaignAction); each page's loader then
// reloads.
export async function action({ request }: Route.ActionArgs) {
  return runCampaignAction(await request.formData());
}
