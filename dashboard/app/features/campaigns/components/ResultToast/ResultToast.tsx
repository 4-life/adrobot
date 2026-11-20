import type { ReactNode } from "react";

import type { ToastTone } from "@/components/shared/Toast/Toaster";

import type { ActionResult } from "../../types";
import { PushAllResults } from "../PushAllResults/PushAllResults";

type Toast = { tone: ToastTone; content: ReactNode };

// What a campaign action's result says, as toasts: its error, its message, and anything the
// tracker stored differently from what was sent. An action with nothing to say gives none.
export function resultToasts(result: ActionResult): Toast[] {
  if (!result.ok) {
    return [{ tone: "error", content: result.error }];
  }
  const toasts: Toast[] = [];
  if (result.message) {
    toasts.push({
      tone: "success",
      content: (
        <>
          {result.message}
          {result.pushResults && result.pushResults.length > 0 && (
            <div className="mt-1">
              <PushAllResults results={result.pushResults} />
            </div>
          )}
        </>
      ),
    });
  }
  if (result.mismatch && result.mismatch.length > 0) {
    toasts.push({
      tone: "warning",
      content: (
        <>
          The tracker stored something else than was sent:
          <ul className="mt-1 list-disc pl-5">
            {result.mismatch.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </>
      ),
    });
  }
  return toasts;
}
