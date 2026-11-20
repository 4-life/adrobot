import { useEffect, useState } from "react";
import { useFetcher } from "react-router";

import { TextInput } from "@/components/shared/Field/Field";
import { Spinner } from "@/components/shared/Spinner/Spinner";

import type { LookupItem } from "../../types";

const DEBOUNCE_MS = 250;
export const OFFER_SEARCH_ROUTE = "/offers-search";

// Searches the tracker's active offers by name or id as you type (the list is cached for 60 s).
export function OfferSearch({
  onPick,
  excluded,
  disabled,
}: {
  onPick: (offer: LookupItem) => void;
  excluded: number[]; // already in the stream: shown, not pickable
  disabled?: boolean;
}) {
  const fetcher = useFetcher<LookupItem[]>();
  const [query, setQuery] = useState("");
  const { load } = fetcher;

  useEffect(() => {
    if (!query.trim()) {
      return;
    }
    const timer = setTimeout(() => {
      void load(`${OFFER_SEARCH_ROUTE}?q=${encodeURIComponent(query.trim())}`);
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query, load]);

  const results = query.trim() ? (fetcher.data ?? []) : [];

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <TextInput
          aria-label="Search offers"
          placeholder="Search offers by name or id"
          value={query}
          disabled={disabled}
          onChange={(event) => setQuery(event.target.value)}
          className="max-w-sm"
        />
        {fetcher.state !== "idle" && <Spinner label="Searching offers" />}
      </div>
      {results.length > 0 && (
        <ul className="max-h-56 max-w-sm overflow-auto rounded-md border bg-popover text-sm">
          {results.map((offer) => {
            const taken = excluded.includes(offer.id);
            return (
              <li key={offer.id}>
                <button
                  type="button"
                  disabled={taken || disabled}
                  onClick={() => {
                    onPick(offer);
                    setQuery("");
                  }}
                  className="flex w-full justify-between px-2.5 py-1.5 text-left hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span>{offer.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {taken ? "already in" : `#${offer.id}`}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
