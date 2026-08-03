import { resolveMediaUrl } from "@/lib/media";
import type {
  MediaVariant,
  MediaVariantIntent,
  PublicMedia,
} from "@/lib/types/public-media";

const FALLBACK_ORDER: Record<MediaVariantIntent, readonly string[]> = {
  thumbnail: ["thumbnail", "card", "display", "full", "legacy"],
  card: ["card", "display", "thumbnail", "full", "legacy"],
  display: ["display", "full", "card", "thumbnail", "legacy"],
  full: ["full", "display", "card", "legacy"],
  og: ["og", "display", "card", "legacy"],
};

const CONVENIENCE_FIELDS: Record<string, keyof PublicMedia> = {
  thumbnail: "thumbnail_url",
  card: "card_url",
  display: "display_url",
  full: "full_url",
  og: "og_url",
};

function variantEntryUrl(
  entry: MediaVariant | string | null | undefined,
): string | null {
  if (!entry) return null;
  if (typeof entry === "string") return entry || null;
  return entry.url || null;
}

function selectVariantUrl(
  media: PublicMedia | null,
  intent: MediaVariantIntent,
  legacyUrl?: string | null,
): string | null {
  if (!media && !legacyUrl) return null;
  const normalized = media ?? {};
  const variants =
    normalized.variants && typeof normalized.variants === "object"
      ? normalized.variants
      : {};
  const order = FALLBACK_ORDER[intent] ?? FALLBACK_ORDER.display;

  for (const key of order) {
    if (key === "legacy") {
      return (
        legacyUrl ??
        normalized.url ??
        normalized.display_url ??
        normalized.legacy_url ??
        null
      );
    }

    const convenienceField = CONVENIENCE_FIELDS[key];
    const convenience = convenienceField
      ? (normalized[convenienceField] as string | null | undefined)
      : undefined;
    if (convenience) return convenience;
    if (key === "display" && normalized.url) return normalized.url;

    const fromVariants = variantEntryUrl(
      variants[key as keyof typeof variants],
    );
    if (fromVariants) return fromVariants;
  }

  return legacyUrl ?? null;
}

function resolveSelectedUrl(
  url: string | null | undefined,
): string | null {
  if (!url) return null;
  const resolved = resolveMediaUrl(url);
  return resolved || null;
}

export function normalizePublicMedia(
  input: PublicMedia | string | null | undefined,
  legacyUrl?: string | null,
): PublicMedia | null {
  if (input == null) {
    if (!legacyUrl) return null;
    return fromLegacyUrl(legacyUrl);
  }
  if (typeof input === "string") {
    return fromLegacyUrl(input);
  }
  if (!input.url && !input.display_url && legacyUrl) {
    return { ...input, url: legacyUrl, legacy_url: input.legacy_url ?? legacyUrl };
  }
  return input;
}

export function fromLegacyUrl(
  url: string | null | undefined,
): PublicMedia | null {
  if (!url) return null;
  return {
    url,
    display_url: url,
    legacy_url: url,
  };
}

export function fromMemoryMedia(input: {
  url: string;
  thumbnail_url?: string | null;
  width?: number | null;
  height?: number | null;
  caption?: string | null;
}): PublicMedia {
  const dims = {
    width: input.width ?? null,
    height: input.height ?? null,
  };
  return {
    url: input.url,
    display_url: input.url,
    full_url: input.url,
    thumbnail_url: input.thumbnail_url ?? null,
    alt: input.caption ?? null,
    width: dims.width,
    height: dims.height,
    variants: {
      thumbnail: input.thumbnail_url
        ? { url: input.thumbnail_url, ...dims }
        : undefined,
      display: { url: input.url, ...dims },
      full: { url: input.url, ...dims },
    },
  };
}

function pickVariant(
  media: PublicMedia | null | undefined,
  intent: MediaVariantIntent,
  legacyUrl?: string | null,
): string | null {
  const normalized = normalizePublicMedia(media ?? null, legacyUrl);
  return resolveSelectedUrl(
    selectVariantUrl(normalized, intent, legacyUrl),
  );
}

export function getMediaThumbnail(
  media: PublicMedia | null | undefined,
  legacyUrl?: string | null,
): string | null {
  return pickVariant(media, "thumbnail", legacyUrl);
}

export function getMediaCard(
  media: PublicMedia | null | undefined,
  legacyUrl?: string | null,
): string | null {
  return pickVariant(media, "card", legacyUrl);
}

export function getMediaDisplay(
  media: PublicMedia | null | undefined,
  legacyUrl?: string | null,
): string | null {
  return pickVariant(media, "display", legacyUrl);
}

export function getMediaFull(
  media: PublicMedia | null | undefined,
  legacyUrl?: string | null,
): string | null {
  return pickVariant(media, "full", legacyUrl);
}

export function getMediaOg(
  media: PublicMedia | null | undefined,
  legacyUrl?: string | null,
): string | null {
  return pickVariant(media, "og", legacyUrl);
}

export function getMediaAspectRatio(
  media: PublicMedia | null | undefined,
): number | null {
  if (!media) return null;

  const topLevel =
    media.width && media.height && media.width > 0 && media.height > 0
      ? media.width / media.height
      : null;
  if (topLevel) return topLevel;

  const variants = media.variants;
  if (!variants) return null;

  for (const key of ["display", "full", "card", "thumbnail"] as const) {
    const entry = variants[key];
    if (entry && typeof entry === "object") {
      const { width, height } = entry;
      if (width && height && width > 0 && height > 0) {
        return width / height;
      }
    }
  }

  return null;
}
