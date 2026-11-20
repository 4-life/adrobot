import { Button } from "@/components/shared/Button/Button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog/ConfirmDialog";
import { Notice } from "@/components/shared/Notice/Notice";

import { useCampaignAction } from "../../useCampaignAction";
import { ActionFeedback } from "../ActionFeedback/ActionFeedback";

// The tracker changed under a pending draft: keep the draft (and push it over) or cancel it.
export function ConflictBanner({ campaignId }: { campaignId: number }) {
  const action = useCampaignAction();

  return (
    <div className="space-y-2">
      <Notice tone="warning">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>The tracker changed this campaign since your draft was started.</span>
          <span className="flex gap-2">
            <ConfirmDialog
              trigger="Cancel my draft"
              title="Cancel the draft?"
              confirmLabel="Cancel draft"
              confirmVariant="danger"
              variant="ghost"
              disabled={action.busy}
              onConfirm={() => action.run("resolve", { campaignId, keepDraft: false })}
            >
              The draft goes back to what the tracker has now.
            </ConfirmDialog>
            <Button
              size="sm"
              disabled={action.busy}
              onClick={() => action.run("resolve", { campaignId, keepDraft: true })}
            >
              Keep my draft
            </Button>
          </span>
        </div>
      </Notice>
      <ActionFeedback result={action.result} />
    </div>
  );
}
