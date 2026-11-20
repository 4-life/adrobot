import type { ReactNode } from "react";

import { Button } from "@/components/shared/Button/Button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog/ConfirmDialog";
import { Spinner } from "@/components/shared/Spinner/Spinner";

import { formatTime } from "../../filters";
import { useCampaignAction } from "../../useCampaignAction";
import { ActionFeedback } from "../ActionFeedback/ActionFeedback";
import { PushAllResults } from "../PushAllResults/PushAllResults";

// Header actions: Fetch streams, the pending count, Push all and Cancel all.
export function SyncBar({
  pending,
  lastFetched,
  newCampaign,
}: {
  pending: number;
  lastFetched: string | null;
  newCampaign: ReactNode;
}) {
  const action = useCampaignAction();
  const result = action.result;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-end gap-2">
        {action.busy && <Spinner label="Working" />}
        <span className="text-xs text-muted-foreground">
          {lastFetched ? `Fetched ${formatTime(lastFetched)}` : "Never fetched"}
        </span>
        <Button disabled={action.busy} onClick={() => action.run("fetch")}>
          Fetch streams
        </Button>
        {newCampaign}
        <span className="text-sm">
          <strong>{pending}</strong> pending
        </span>
        <ConfirmDialog
          trigger="Cancel all"
          title={`Cancel all ${pending} pending campaigns?`}
          confirmLabel="Cancel all"
          confirmVariant="danger"
          variant="ghost"
          disabled={!pending || action.busy}
          onConfirm={() => action.run("cancel-all")}
        >
          Every draft goes back to what the tracker has; new drafts are deleted. Nothing in the tracker
          changes.
        </ConfirmDialog>
        <ConfirmDialog
          trigger="Push all"
          title={`Push all ${pending} pending campaigns to the tracker?`}
          confirmLabel="Push all"
          variant="primary"
          disabled={!pending || action.busy}
          onConfirm={() => action.run("push-all")}
        >
          Each campaign is pushed in turn; one that fails (a conflict, an invalid draft) doesn't stop
          the rest.
        </ConfirmDialog>
      </div>
      <ActionFeedback result={result} />
      {result?.ok && result.pushResults && <PushAllResults results={result.pushResults} />}
    </div>
  );
}
