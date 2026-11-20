import { type ReactNode, useEffect, useRef } from "react";

// A modal on the native <dialog>: focus trap, Escape and the backdrop come with it.
export function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) {
      return;
    }
    if (open && !dialog.open) {
      dialog.showModal();
    }
    if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className="m-auto w-full max-w-lg rounded-lg border bg-popover p-0 text-popover-foreground backdrop:bg-black/60"
    >
      {open && (
        <div className="space-y-4 p-5">
          <h2 className="text-base font-semibold">{title}</h2>
          {children}
        </div>
      )}
    </dialog>
  );
}
