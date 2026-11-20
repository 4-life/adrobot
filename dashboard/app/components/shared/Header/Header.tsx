import type { ReactNode } from "react";

// The page header: the app name, and the page's own actions on the right.
export function Header({ actions }: { actions?: ReactNode }) {
  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 p-4">
        <h1 className="text-lg font-semibold">AdRobot</h1>
        {actions}
      </div>
    </header>
  );
}
