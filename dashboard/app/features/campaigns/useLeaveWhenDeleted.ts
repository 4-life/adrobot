import { useEffect } from "react";
import { useNavigate } from "react-router";

import type { ActionResult } from "./types";

// A cancelled new draft is deleted: its page is gone, so go back to the campaigns table.
export function useLeaveWhenDeleted(result: ActionResult | undefined) {
  const navigate = useNavigate();
  const deleted = Boolean(result?.ok && result.deleted);

  useEffect(() => {
    if (deleted) {
      void navigate("/");
    }
  }, [deleted, navigate]);
}
