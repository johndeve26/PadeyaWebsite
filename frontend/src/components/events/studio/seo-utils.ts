import type { EventStudioValues } from "./types";

export type SeoSuggestions = {
  seo_title: string;
  seo_description: string;
  social_share_title: string;
  social_share_description: string;
  hashtags: string;
  discoverable_keywords: string;
};

/** Public-safe place for SEO/social — never the private street address. */
export function publicSeoPlaceLabel(values: EventStudioValues): string {
  if (values.location_visibility === "online_only") {
    return values.public_location_label.trim() || "Online Event";
  }
  if (values.public_location_label.trim()) {
    return values.public_location_label.trim();
  }
  if (values.location_visibility === "full_public") {
    return (
      [values.area || values.city, values.state].filter(Boolean).join(", ") || ""
    );
  }
  // Hidden / area_only — city or area only, never street or private venue name.
  return values.area || values.city || "";
}

export function scrubPrivateAddress(
  text: string,
  address: string | null | undefined,
): string {
  const raw = address?.trim();
  if (!raw || !text) return text;
  let next = text;
  if (next.includes(raw)) {
    next = next.split(raw).join("").replace(/\s{2,}/g, " ").trim();
  }
  // Also strip common “street + area” leftovers when the full address was pasted.
  const firstLine = raw.split(",")[0]?.trim();
  if (firstLine && firstLine.length >= 6 && next.includes(firstLine)) {
    next = next.split(firstLine).join("").replace(/\s{2,}/g, " ").trim();
  }
  return next.replace(/^[\s·|,:-]+|[\s·|,:-]+$/g, "").trim();
}

export function seoFieldsContainPrivateAddress(
  values: EventStudioValues,
): boolean {
  const address = values.address.trim();
  if (!address) return false;
  const blob = [
    values.seo_title,
    values.seo_description,
    values.social_share_title,
    values.social_share_description,
    values.hashtags,
    values.discoverable_keywords,
  ].join("\n");
  return blob.includes(address) || blob.includes(address.split(",")[0]?.trim() || "");
}

function slugTag(value: string): string {
  return value
    .replace(/[^a-zA-Z0-9]+/g, "")
    .slice(0, 24);
}

/** Suggest SEO/social copy from title, category, and public city — never address. */
export function suggestSeoCopy(
  values: EventStudioValues,
  categoryName?: string | null,
): SeoSuggestions {
  const title = values.title.trim() || "Your event";
  const place = publicSeoPlaceLabel(values);
  const category = categoryName?.trim() || "";
  const vibe = values.vibe.trim();
  const tagline = values.short_tagline.trim();
  const descSeed =
    tagline ||
    values.description.trim().replace(/\s+/g, " ").slice(0, 140) ||
    "";

  const titleParts = [title];
  if (category) titleParts.push(category);
  if (place) titleParts.push(place);
  const seo_title = titleParts.join(" · ").slice(0, 70);

  const descBits = [
    title,
    category ? `a ${category} event` : null,
    place ? `in ${place}` : null,
  ].filter(Boolean);
  let seo_description = `${descBits.join(" — ")}.`;
  if (vibe) seo_description += ` ${vibe}.`;
  if (tagline && tagline !== vibe) seo_description += ` ${tagline}`;
  else if (descSeed && !tagline) seo_description += ` ${descSeed}`;
  seo_description = scrubPrivateAddress(
    seo_description.replace(/\s+/g, " ").trim().slice(0, 160),
    values.address,
  );

  const social_share_title = (title + (place ? ` · ${place}` : "")).slice(0, 70);
  const social_share_description = scrubPrivateAddress(
    (
      tagline ||
      (category && place
        ? `${category} in ${place} on Pàdéyá.`
        : place
          ? `Join us in ${place} — tickets on Pàdéyá.`
          : "Tickets and details on Pàdéyá.")
    ).slice(0, 160),
    values.address,
  );

  const tags = [
    "Padeya",
    place ? slugTag(place.split(",")[0] || place) : "",
    category ? slugTag(category) : "",
    vibe ? slugTag(vibe) : "",
  ]
    .filter(Boolean)
    .map((t) => `#${t}`);

  const keywords = [
    title,
    category,
    place.split(",")[0]?.trim() || place,
    vibe,
    "tickets",
    "events",
  ]
    .map((k) => k.trim())
    .filter(Boolean);

  return {
    seo_title: scrubPrivateAddress(seo_title, values.address),
    seo_description,
    social_share_title: scrubPrivateAddress(social_share_title, values.address),
    social_share_description,
    hashtags: tags.join(", "),
    discoverable_keywords: [...new Set(keywords)].join(", "),
  };
}

export function resolvedSeoFields(
  values: EventStudioValues,
  categoryName?: string | null,
): SeoSuggestions {
  const suggested = suggestSeoCopy(values, categoryName);
  return {
    seo_title: values.seo_title.trim() || suggested.seo_title,
    seo_description: values.seo_description.trim() || suggested.seo_description,
    social_share_title:
      values.social_share_title.trim() || suggested.social_share_title,
    social_share_description:
      values.social_share_description.trim() ||
      suggested.social_share_description,
    hashtags: values.hashtags.trim() || suggested.hashtags,
    discoverable_keywords:
      values.discoverable_keywords.trim() || suggested.discoverable_keywords,
  };
}
