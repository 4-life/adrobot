import { Button } from "@/components/shared/Button/Button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog/ConfirmDialog";
import { Spinner } from "@/components/shared/Spinner/Spinner";

import type { Campaign } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";
import { ActionFeedback } from "../ActionFeedback/ActionFeedback";

// Push to KT / Cancel changes for one campaign.
export function CampaignActions({ campaign, blocked }: { campaign: Campaign; blocked: boolean }) {
  const action = useCampaignAction();
  const canAct = campaign.pending && !action.busy;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-end gap-2">
        {action.busy && <Spinner label="Working" />}
        <ConfirmDialog
          trigger={campaign.is_new ? "Delete draft" : "Cancel changes"}
          title={campaign.is_new ? "Delete this new draft?" : "Cancel this campaign's changes?"}
          confirmLabel={campaign.is_new ? "Delete draft" : "Cancel changes"}
          confirmVariant="danger"
          variant="ghost"
          disabled={!canAct}
          onConfirm={() => action.run("cancel", { campaignId: campaign.id })}
        >
          {campaign.is_new
            ? "It was never pushed: the draft is deleted."
            : "The draft goes back to what the tracker has. Nothing in the tracker changes."}
        </ConfirmDialog>
        <Button
          variant="primary"
          disabled={!canAct || blocked}
          onClick={() => action.run("push", { campaignId: campaign.id })}
        >
          Push to KT
        </Button>
      </div>
      <ActionFeedback result={action.result} />
    </div>
  );
}
