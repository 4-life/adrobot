import { type ReactNode, useState } from "react";

import { Button } from "@/components/shared/Button/Button";
import { Dialog } from "@/components/shared/Dialog/Dialog";

type Variant = "primary" | "secondary" | "danger" | "ghost";

// A button that asks first: the action runs only on "confirm" (never window.confirm).
export function ConfirmDialog({
  trigger,
  title,
  children,
  confirmLabel,
  onConfirm,
  variant = "secondary",
  confirmVariant = "primary",
  disabled,
}: {
  trigger: ReactNode;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  variant?: Variant;
  confirmVariant?: Variant;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button variant={variant} disabled={disabled} onClick={() => setOpen(true)}>
        {trigger}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} title={title}>
        <div className="text-sm text-muted-foreground">{children}</div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Back
          </Button>
          <Button
            variant={confirmVariant}
            onClick={() => {
              setOpen(false);
              onConfirm();
            }}
          >
            {confirmLabel}
          </Button>
        </div>
      </Dialog>
    </>
  );
}
