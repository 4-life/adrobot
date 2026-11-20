import { useEffect, useRef, useState } from "react";
import { useFetcher, useNavigate } from "react-router";

import { Button } from "@/components/shared/Button/Button";
import { Dialog } from "@/components/shared/Dialog/Dialog";
import { Field, Select, TextInput } from "@/components/shared/Field/Field";
import { Notice } from "@/components/shared/Notice/Notice";
import { Spinner } from "@/components/shared/Spinner/Spinner";

import { formatCountries } from "../../countries";
import type { LookupItem, NewCampaignData } from "../../types";
import { useCampaignAction } from "../../useCampaignAction";
import { OfferSearch } from "../OfferSearch/OfferSearch";

const DATA_ROUTE = "/new-campaign-data";

type Form = {
  name: string;
  alias: string;
  countries: string;
  domainId: string;
  groupId: string;
  sourceId: string;
  offers: LookupItem[];
};

const EMPTY: Form = {
  name: "",
  alias: "",
  countries: "",
  domainId: "",
  groupId: "",
  sourceId: "",
  offers: [],
};

function OptionalSelect({
  label,
  items,
  value,
  onChange,
  required,
}: {
  label: string;
  items: LookupItem[];
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <Field label={label}>
      <Select value={value} required={required} onChange={(event) => onChange(event.target.value)}>
        <option value="">{required ? `Choose a ${label.toLowerCase()}` : "None"}</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
    </Field>
  );
}

function PickedOffers({ offers, onRemove }: { offers: LookupItem[]; onRemove: (id: number) => void }) {
  if (offers.length === 0) {
    return <p className="text-xs text-muted-foreground">No offers yet: search and pick at least one.</p>;
  }
  return (
    <ul className="divide-y rounded-md border text-sm">
      {offers.map((offer) => (
        <li key={offer.id} className="flex items-center justify-between px-2.5 py-1.5">
          <span>
            {offer.name} <span className="text-xs text-muted-foreground">#{offer.id}</span>
          </span>
          <Button size="sm" variant="ghost" onClick={() => onRemove(offer.id)}>
            Remove
          </Button>
        </li>
      ))}
    </ul>
  );
}

// "New campaign": a draft with name, geo, domain / group / source and offers. It's only
// created in the tracker when pushed.
export function NewCampaignDialog() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Form>(EMPTY);
  const data = useFetcher<NewCampaignData>();
  // No toasts: the modal would hide them; its error is shown inside the dialog.
  const action = useCampaignAction({ toasts: false });
  const submitted = useRef(false);
  const set = (patch: Partial<Form>) => setForm((current) => ({ ...current, ...patch }));

  const { load } = data;
  useEffect(() => {
    if (open) {
      void load(DATA_ROUTE);
    }
  }, [open, load]);

  // Prefill the name, alias and countries from the defaults, once per opening.
  const defaults = data.data?.ok ? data.data.defaults : null;
  useEffect(() => {
    if (open && defaults) {
      setForm((current) =>
        current.name
          ? current
          : {
              ...current,
              name: defaults.name,
              alias: defaults.alias,
              countries: formatCountries(defaults.countries),
            },
      );
    }
  }, [open, defaults]);

  // Once the draft is created: close, and open its page.
  const navigate = useNavigate();
  useEffect(() => {
    const result = action.result;
    if (submitted.current && !action.busy && result?.ok) {
      submitted.current = false;
      setOpen(false);
      setForm(EMPTY);
      if (result.campaignId) {
        void navigate(`/campaigns/${result.campaignId}`);
      }
    }
  }, [action.busy, action.result, navigate]);

  const close = () => {
    setOpen(false);
    setForm(EMPTY);
  };

  const lists = data.data?.ok ? data.data : null;
  const canCreate = Boolean(form.domainId) && form.offers.length > 0 && !action.busy;

  return (
    <>
      <Button variant="primary" onClick={() => setOpen(true)}>
        New campaign
      </Button>
      <Dialog open={open} onClose={close} title="New campaign">
        {data.state !== "idle" && !lists && <Spinner label="Loading the tracker's lists" />}
        {data.data && !data.data.ok && <Notice tone="error">{data.data.error}</Notice>}
        {lists && (
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              submitted.current = true;
              action.run("create", {
                name: form.name,
                alias: form.alias,
                countries: form.countries,
                domainId: form.domainId,
                groupId: form.groupId || null,
                sourceId: form.sourceId || null,
                offerIds: form.offers.map((o) => o.id),
              });
            }}
          >
            <Field label="Name">
              <TextInput value={form.name} onChange={(event) => set({ name: event.target.value })} />
            </Field>
            <Field label="Alias" hint="In the campaign URL: https://<domain>/<alias>">
              <TextInput value={form.alias} onChange={(event) => set({ alias: event.target.value })} />
            </Field>
            <Field label="Geo" hint={`Visitors from these countries go to ${lists.defaults.redirect_url}`}>
              <TextInput
                placeholder="AU, NZ"
                value={form.countries}
                onChange={(event) => set({ countries: event.target.value })}
              />
            </Field>
            <OptionalSelect
              label="Domain"
              items={lists.domains}
              value={form.domainId}
              onChange={(domainId) => set({ domainId })}
              required
            />
            <OptionalSelect label="Group" items={lists.groups} value={form.groupId} onChange={(groupId) => set({ groupId })} />
            <OptionalSelect
              label="Traffic source"
              items={lists.sources}
              value={form.sourceId}
              onChange={(sourceId) => set({ sourceId })}
            />
            <div className="space-y-1.5 text-sm">
              <span className="font-medium">Offers</span>
              <OfferSearch
                excluded={form.offers.map((o) => o.id)}
                onPick={(offer) => set({ offers: [...form.offers, offer] })}
              />
              <PickedOffers
                offers={form.offers}
                onRemove={(offerId) => set({ offers: form.offers.filter((o) => o.id !== offerId) })}
              />
              <p className="text-xs text-muted-foreground">
                Shares are split equally; pin them on the campaign card after creating.
              </p>
            </div>
            {action.error && <Notice tone="error">{action.error}</Notice>}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={close}>
                Back
              </Button>
              <Button type="submit" variant="primary" disabled={!canCreate}>
                Create draft
              </Button>
            </div>
          </form>
        )}
      </Dialog>
    </>
  );
}
