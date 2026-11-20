import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

import { cn } from "@/lib/utils";

export type ToastTone = "success" | "info" | "warning" | "error";

type Toast = { id: number; tone: ToastTone; content: ReactNode };
type ShowToast = (tone: ToastTone, content: ReactNode) => void;

// Errors stay until closed; the rest close by themselves.
const DURATION_MS: Record<ToastTone, number | null> = {
  success: 4_000,
  info: 4_000,
  warning: 10_000,
  error: null,
};

const TONES: Record<ToastTone, string> = {
  success: "border-emerald-500/40 bg-emerald-950 text-emerald-100",
  info: "border-sky-500/40 bg-sky-950 text-sky-100",
  warning: "border-amber-500/40 bg-amber-950 text-amber-100",
  error: "border-red-500/40 bg-red-950 text-red-100",
};

const ToastContext = createContext<ShowToast>(() => {});

// Wraps the app (root.tsx); anything inside shows a toast with useToast().
export function Toaster({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback<ShowToast>(
    (tone, content) => {
      nextId.current += 1;
      const id = nextId.current;
      setToasts((current) => [...current, { id, tone, content }]);
      const duration = DURATION_MS[tone];
      if (duration !== null) {
        setTimeout(() => dismiss(id), duration);
      }
    },
    [dismiss],
  );

  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ol
        aria-live="polite"
        className="fixed right-4 bottom-4 z-50 flex w-full max-w-sm flex-col gap-2"
      >
        {toasts.map((toast) => (
          <li
            key={toast.id}
            role={toast.tone === "error" ? "alert" : "status"}
            className={cn(
              "flex items-start gap-3 rounded-md border px-3 py-2 text-sm shadow-lg",
              TONES[toast.tone],
            )}
          >
            <div className="min-w-0 flex-1">{toast.content}</div>
            <button
              type="button"
              aria-label="Close"
              onClick={() => dismiss(toast.id)}
              className="shrink-0 opacity-60 hover:opacity-100"
            >
              ×
            </button>
          </li>
        ))}
      </ol>
    </ToastContext.Provider>
  );
}

export function useToast(): ShowToast {
  return useContext(ToastContext);
}
