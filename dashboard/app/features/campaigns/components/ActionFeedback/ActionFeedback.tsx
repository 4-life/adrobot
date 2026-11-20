import { Notice } from "@/components/shared/Notice/Notice";

import type { ActionResult } from "../../types";

// What the last action said: its error, its message, and anything the tracker stored differently.
export function ActionFeedback({ result }: { result: ActionResult | undefined }) {
  if (!result) {
    return null;
  }
  if (!result.ok) {
    return <Notice tone="error">{result.error}</Notice>;
  }
  return (
    <>
      {result.message && <Notice>{result.message}</Notice>}
      {result.mismatch && result.mismatch.length > 0 && (
        <Notice tone="warning">
          The tracker stored something else than was sent:
          <ul className="mt-1 list-disc pl-5">
            {result.mismatch.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Notice>
      )}
    </>
  );
}
