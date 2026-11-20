import { useEffect, useState } from "react";
import { useFetcher } from "react-router";

import { TextInput } from "@/components/shared/Field/Field";
import { Spinner } from "@/components/shared/Spinner/Spinner";

import type { LookupItem } from "../../types";

const DEBOUNCE_MS = 250;
const CLOSE_DELAY_MS = 150; // closes the list shortly after the input loses focus
export const OFFER_SEARCH_ROUTE = "/offers-search";

function offerNote(offer: LookupItem): string {
  return offer.active ? `#${offer.id}` : `#${offer.id} · archived`;
}

// Every tracker offer not already in the stream, narrowed by name or id as you type (the list
// is cached for 60 s). Opens on focus with all of them; archived ones are shown, not pickable.
export function OfferSearch({
  onPick,
  excluded,
  disabled,
}: {
  onPick: (offer: LookupItem) => void;
  excluded: number[]; // already in the stream: hidden
  disabled?: boolean;
}) {
  const fetcher = useFetcher<LookupItem[]>();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const { load } = fetcher;

  useEffect(() => {
    if (!open) {
      return;
    }
    const timer = setTimeout(() => {
      void load(`${OFFER_SEARCH_ROUTE}?q=${encodeURIComponent(query.trim())}`);
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [open, query, load]);

  const results = open ? (fetcher.data ?? []).filter((o) => !excluded.includes(o.id)) : [];

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <TextInput
          type="search"
          aria-label="Search offers"
          placeholder="Search offers by name or id"
          value={query}
          disabled={disabled}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), CLOSE_DELAY_MS)}
          onChange={(event) => setQuery(event.target.value)}
          className="max-w-sm"
        />
        {fetcher.state !== "idle" && <Spinner label="Searching offers" />}
        {open && fetcher.data && (
          <span className="text-xs text-muted-foreground">{results.length} offers</span>
        )}
      </div>
      {results.length > 0 && (
        <ul
          // Keeps focus in the input while a result is pressed: the blur would otherwise close
          // the list before the click lands, and the pick would be lost.
          onMouseDown={(event) => event.preventDefault()}
          className="max-h-72 max-w-sm overflow-auto rounded-md border bg-popover text-sm"
        >
          {results.map((offer) => (
              <li key={offer.id}>
                <button
                  type="button"
                  disabled={!offer.active || disabled}
                  onClick={() => {
                    onPick(offer);
                    setQuery("");
                    setOpen(false);
                  }}
                  className="flex w-full justify-between gap-3 px-2.5 py-1.5 text-left hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="truncate">{offer.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{offerNote(offer)}</span>
                </button>
              </li>
          ))}
        </ul>
      )}
    </div>
  );
}
