"use client";

import { useEffect, useState } from "react";

import { Button, Input, Select, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchVenueTypes,
  suggestVenueType,
  type TaxonomyVocabTerm,
} from "@/lib/taxonomy-api";

import { EventStudioSection } from "../EventStudioSection";
import { LocationMapFields } from "../LocationMapFields";
import { LocationPrivacySelector } from "../LocationPrivacySelector";
import { LocationPublicPreview } from "../LocationPublicPreview";
import { LocationTaxonomyFields } from "../LocationTaxonomyFields";
import { StudioFieldGroup } from "../studio-ui";
import type { EventStudioValues } from "../types";

const VENUE_TYPE_OTHER = "__suggest_venue_type__";

const POSTCODE_COUNTRIES = new Set([
  "united kingdom",
  "uk",
  "gb",
  "united states",
  "usa",
  "us",
  "canada",
  "ca",
  "ireland",
  "ie",
  "australia",
  "au",
]);

function countryUsesPostcode(country: string): boolean {
  const key = country.trim().toLowerCase();
  if (!key) return false;
  return POSTCODE_COUNTRIES.has(key);
}

export function LocationStep({
  values,
  onChange,
}: {
  values: EventStudioValues;
  onChange: <K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) => void;
}) {
  const [venueTypes, setVenueTypes] = useState<TaxonomyVocabTerm[]>([]);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [suggestName, setSuggestName] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const onlineOnly = values.location_visibility === "online_only";
  const showPublicAreaLabel =
    values.location_visibility !== "full_public" && !onlineOnly;

  useEffect(() => {
    let alive = true;
    void fetchVenueTypes()
      .then((rows) => {
        if (alive) setVenueTypes(rows);
      })
      .catch(() => {
        if (alive) setVenueTypes([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  async function submitVenueTypeSuggest() {
    const name = suggestName.trim();
    if (name.length < 2) {
      setSuggestError("Enter a venue type (at least 2 characters).");
      return;
    }
    setSuggesting(true);
    setSuggestError(null);
    try {
      const created = await suggestVenueType({ name });
      const rows = await fetchVenueTypes();
      setVenueTypes(rows);
      onChange("venue_type", created.slug);
      setSuggestOpen(false);
      setSuggestName("");
    } catch (err) {
      setSuggestError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Could not save venue type.",
      );
    } finally {
      setSuggesting(false);
    }
  }

  return (
    <EventStudioSection
      title="Location & Privacy"
      description="Hosts and admins always keep the full private address. Public pages only show what your visibility rules allow."
    >
      <LocationMapFields
        values={values}
        onChange={onChange}
        disabled={onlineOnly}
      />

      <StudioFieldGroup title="Selected venue">
        <Input
          label="Venue name"
          hint="Club, hotel, hall — shown publicly only when visibility allows."
          value={values.venue_name}
          onChange={(e) => onChange("venue_name", e.target.value)}
          disabled={onlineOnly}
        />
        <Input
          label="Address / location text"
          hint="Full street address for you, staff, and eligible ticket holders."
          value={values.address}
          onChange={(e) => onChange("address", e.target.value)}
          disabled={onlineOnly}
          placeholder="14 Palm Close, Lekki Phase 1"
        />
        {countryUsesPostcode(values.country) && !onlineOnly ? (
          <Input
            label="Postcode"
            value={values.postcode}
            onChange={(e) => onChange("postcode", e.target.value)}
          />
        ) : null}
        {showPublicAreaLabel ? (
          <Input
            label="Area fans see before exact address"
            hint="City or area line on cards and the public page when the street is hidden."
            value={values.public_location_label}
            onChange={(e) => onChange("public_location_label", e.target.value)}
            placeholder="Lekki Phase 1, Lagos — exact venue revealed after purchase."
          />
        ) : null}
      </StudioFieldGroup>

      <LocationTaxonomyFields values={values} onChange={onChange} />

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Venue type"
          hint="Pick a type or choose Other… to suggest a new one for all hosts."
          value={suggestOpen ? VENUE_TYPE_OTHER : values.venue_type}
          onChange={(e) => {
            const next = e.target.value;
            if (next === VENUE_TYPE_OTHER) {
              setSuggestOpen(true);
              setSuggestError(null);
              return;
            }
            setSuggestOpen(false);
            setSuggestName("");
            setSuggestError(null);
            onChange("venue_type", next);
          }}
          disabled={onlineOnly}
        >
          <option value="">Select venue type</option>
          {venueTypes.map((type) => (
            <option key={type.id} value={type.slug}>
              {type.name}
            </option>
          ))}
          {!onlineOnly ? (
            <option value={VENUE_TYPE_OTHER}>Other…</option>
          ) : null}
        </Select>
      </div>

      {suggestOpen && !onlineOnly ? (
        <div className="rounded-[var(--radius-lg)] border border-border bg-card/80 p-4 dark:bg-surface-elevated/80">
          <p className="text-sm font-semibold text-foreground">
            Suggest a new venue type
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Saved for other hosts to select next time (e.g. “Beach house”, “Cinema”).
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="min-w-0 flex-1 space-y-1.5">
              <span className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Venue type name
              </span>
              <Input
                value={suggestName}
                onChange={(e) => setSuggestName(e.target.value)}
                placeholder="e.g. Beach house"
                disabled={suggesting}
                maxLength={120}
              />
            </label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={suggesting}
                onClick={() => {
                  setSuggestOpen(false);
                  setSuggestName("");
                  setSuggestError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                type="button"
                disabled={suggesting || suggestName.trim().length < 2}
                onClick={() => void submitVenueTypeSuggest()}
              >
                {suggesting ? "Saving…" : "Save type"}
              </Button>
            </div>
          </div>
          {suggestError ? (
            <p className="mt-2 text-xs font-semibold text-danger">{suggestError}</p>
          ) : null}
        </div>
      ) : null}

      <LocationPrivacySelector
        values={values}
        onChange={(key, value) => onChange(key as keyof EventStudioValues, value)}
      />

      <LocationPublicPreview values={values} />

      {!onlineOnly ? (
        <Textarea
          label="Directions / arrival note"
          rows={3}
          hint="Shown to eligible ticket holders with the exact venue — not on the public page."
          value={values.directions_note}
          onChange={(e) => onChange("directions_note", e.target.value)}
          placeholder="Example: Use the side gate, ask for Hall B, parking is behind the venue."
        />
      ) : null}
    </EventStudioSection>
  );
}
