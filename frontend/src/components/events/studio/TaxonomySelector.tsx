"use client";

import { Button, Input, Select } from "@/components/ui";
import type { EventCategory } from "@/lib/types/events";

import { StudioFieldGroup, StudioMicrocopy } from "./studio-ui";
import type { EventStudioValues } from "./types";

const SUGGESTED_TAGS: Record<string, string[]> = {
  nightlife: ["afrobeats", "vip", "island"],
  music: ["afrobeats", "outdoor"],
  comedy: ["open-mic", "mainland"],
  tech: ["networking", "founders"],
  gospel: ["worship"],
  lifestyle: ["student", "campus"],
  campus: ["student", "mainland"],
};

/**
 * Category / vibe / tags selector for Event Studio discoverability.
 * Prefer this over wiring TaxonomyFields alone — clearer grouping + microcopy.
 */
export function TaxonomySelector({
  values,
  categories,
  onChange,
  onApplyHostDefaults,
}: {
  values: EventStudioValues;
  categories: EventCategory[];
  onChange: (key: keyof EventStudioValues, value: string) => void;
  onApplyHostDefaults?: () => void;
}) {
  const categorySlug =
    categories.find((c) => c.id === values.category_id)?.slug || "";
  const suggestions = SUGGESTED_TAGS[categorySlug] || [];
  const listedNeedsCategory =
    values.visibility === "listed" && !values.category_id;

  return (
    <div className="space-y-4">
      <StudioFieldGroup
        title="Discovery"
        description={
          listedNeedsCategory
            ? "Listed events need a primary category before submit — hubs and related rails depend on it."
            : "Category, vibe, and tags help guests find you on Pàdéyá browse and city hubs."
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Primary category"
            hint={
              listedNeedsCategory
                ? "Required for listed public events."
                : "Browse category for hubs and related rails."
            }
            required={values.visibility === "listed"}
            value={values.category_id}
            onChange={(e) => onChange("category_id", e.target.value)}
            error={
              listedNeedsCategory ? "Select a category for listed events" : undefined
            }
          >
            <option value="">Select category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </Select>
          <Input
            label="Vibe"
            hint="One clear mood guests will recognize."
            value={values.vibe}
            onChange={(e) => onChange("vibe", e.target.value)}
            placeholder="Afrobeats · Rooftop · After-dark"
          />
        </div>
        <Input
          label="Hashtags / tags"
          hint="Comma-separated discovery tags (also used in SEO suggestions)."
          value={values.hashtags}
          onChange={(e) => onChange("hashtags", e.target.value)}
          placeholder="afrobeats, vip, island"
        />
        {suggestions.length ? (
          <div className="flex flex-wrap items-center gap-2">
            <StudioMicrocopy>Suggested:</StudioMicrocopy>
            {suggestions.map((tag) => (
              <button
                key={tag}
                type="button"
                className="rounded-[var(--radius-sm)] border border-border bg-surface-inset px-2.5 py-1 text-xs font-semibold text-foreground transition-colors hover:border-border-strong/30"
                onClick={() => {
                  const parts = values.hashtags
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean);
                  if (!parts.includes(tag)) {
                    onChange("hashtags", [...parts, tag].join(", "));
                  }
                }}
              >
                {tag}
              </button>
            ))}
          </div>
        ) : null}
        {onApplyHostDefaults ? (
          <Button type="button" variant="secondary" size="sm" onClick={onApplyHostDefaults}>
            Apply host defaults
          </Button>
        ) : null}
      </StudioFieldGroup>
    </div>
  );
}

/** @deprecated Prefer TaxonomySelector — kept for import compatibility. */
export { TaxonomySelector as TaxonomyFields };
