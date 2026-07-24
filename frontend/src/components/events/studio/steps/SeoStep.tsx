"use client";

import { useMemo } from "react";

import { Alert, Button, Input, Textarea } from "@/components/ui";
import type { EventCategory } from "@/lib/types/events";
import { absoluteUrl } from "@/lib/seo/site";

import { EventStudioSection } from "../EventStudioSection";
import { SeoPreviewCard } from "../SeoPreviewCard";
import {
  publicSeoPlaceLabel,
  resolvedSeoFields,
  seoFieldsContainPrivateAddress,
  suggestSeoCopy,
} from "../seo-utils";
import type { EventStudioValues } from "../types";

export function SeoStep({
  values,
  categories = [],
  onChange,
}: {
  values: EventStudioValues;
  categories?: EventCategory[];
  onChange: <K extends keyof EventStudioValues>(
    key: K,
    value: EventStudioValues[K],
  ) => void;
}) {
  const categoryName = useMemo(() => {
    if (!values.category_id) return null;
    return categories.find((c) => c.id === values.category_id)?.name ?? null;
  }, [categories, values.category_id]);

  const suggested = useMemo(
    () => suggestSeoCopy(values, categoryName),
    [values, categoryName],
  );
  const resolved = useMemo(
    () => resolvedSeoFields(values, categoryName),
    [values, categoryName],
  );
  const locationLabel = publicSeoPlaceLabel(values);
  const leaksAddress = seoFieldsContainPrivateAddress(values);
  const anyEmpty =
    !values.seo_title.trim() ||
    !values.seo_description.trim() ||
    !values.social_share_title.trim() ||
    !values.social_share_description.trim() ||
    !values.hashtags.trim() ||
    !values.discoverable_keywords.trim();

  function applySuggestions() {
    onChange("seo_title", values.seo_title.trim() || suggested.seo_title);
    onChange(
      "seo_description",
      values.seo_description.trim() || suggested.seo_description,
    );
    onChange(
      "social_share_title",
      values.social_share_title.trim() || suggested.social_share_title,
    );
    onChange(
      "social_share_description",
      values.social_share_description.trim() ||
        suggested.social_share_description,
    );
    onChange("hashtags", values.hashtags.trim() || suggested.hashtags);
    onChange(
      "discoverable_keywords",
      values.discoverable_keywords.trim() || suggested.discoverable_keywords,
    );
  }

  return (
    <EventStudioSection
      title="SEO & Discovery"
      description="Optional wording for Google and social shares. Suggestions use title, category, and public city only — never your private street address."
    >
      <SeoPreviewCard
        title={resolved.seo_title}
        description={resolved.seo_description}
        path={absoluteUrl(values.slug ? `/events/${values.slug}` : "/events/…")}
        locationLabel={locationLabel || undefined}
        socialTitle={resolved.social_share_title}
        socialDescription={resolved.social_share_description}
        imageUrl={
          values.social_share_image_url ||
          values.banner_url ||
          values.mobile_banner_url
        }
      />

      {leaksAddress ? (
        <Alert tone="warning" title="Private address in SEO copy">
          Remove the street address from SEO or social fields. Guests and search
          engines should only see your public location label or city.
        </Alert>
      ) : null}

      {anyEmpty ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-border bg-muted/50 px-4 py-3">
          <p className="text-sm text-muted-foreground">
            Empty fields use suggested copy in the preview
            {categoryName ? ` (${categoryName}` : ""}
            {locationLabel
              ? `${categoryName ? ", " : " ("}${locationLabel}`
              : ""}
            {categoryName || locationLabel ? ")" : ""}.
          </p>
          <Button type="button" variant="secondary" size="sm" onClick={applySuggestions}>
            Use suggested copy
          </Button>
        </div>
      ) : null}

      <Input
        label="SEO title"
        hint="Title that may appear in search results."
        placeholder={suggested.seo_title}
        value={values.seo_title}
        onChange={(e) => onChange("seo_title", e.target.value)}
      />
      <Textarea
        label="SEO description"
        rows={3}
        hint="Short summary for search snippets — city and vibe only, not the private address."
        placeholder={suggested.seo_description}
        value={values.seo_description}
        onChange={(e) => onChange("seo_description", e.target.value)}
      />
      <Input
        label="Social share title"
        hint="Headline when someone shares your link."
        placeholder={suggested.social_share_title}
        value={values.social_share_title}
        onChange={(e) => onChange("social_share_title", e.target.value)}
      />
      <Textarea
        label="Social share description"
        rows={3}
        hint="Short text under the share title — still no secret venue details."
        placeholder={suggested.social_share_description}
        value={values.social_share_description}
        onChange={(e) => onChange("social_share_description", e.target.value)}
      />
      <Input
        label="Hashtags"
        hint="Comma-separated tags for promotion (optional)."
        placeholder={suggested.hashtags}
        value={values.hashtags}
        onChange={(e) => onChange("hashtags", e.target.value)}
      />
      <Input
        label="Discoverable keywords"
        hint="Comma-separated words that help Pàdéyá match your event in browse/search."
        placeholder={suggested.discoverable_keywords}
        value={values.discoverable_keywords}
        onChange={(e) => onChange("discoverable_keywords", e.target.value)}
      />
    </EventStudioSection>
  );
}
