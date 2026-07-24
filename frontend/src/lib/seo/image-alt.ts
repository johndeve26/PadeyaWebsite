/** Concise, non-spammy alt text for public media (Phase 1B). */

export function eventCoverAlt(title: string | null | undefined): string {
  const t = (title || "").trim();
  return t ? `${t} event cover` : "Event cover";
}

export function eventCardAlt(title: string | null | undefined): string {
  const t = (title || "").trim();
  return t ? `${t} event` : "Event";
}

export function hostAvatarAlt(displayName: string | null | undefined): string {
  const n = (displayName || "").trim();
  return n || "Host";
}

export function hostCoverAlt(displayName: string | null | undefined): string {
  const n = (displayName || "").trim();
  return n ? `${n} cover` : "Host cover";
}

export function sponsorLogoAlt(name: string | null | undefined): string {
  const n = (name || "").trim();
  return n ? `${n} logo` : "Sponsor logo";
}

export function sponsorCoverAlt(name: string | null | undefined): string {
  const n = (name || "").trim();
  return n ? `${n} cover` : "Sponsor cover";
}

export function merchImageAlt(
  productName: string | null | undefined,
  opts?: { index?: number; total?: number },
): string {
  const n = (productName || "").trim() || "Product";
  if (
    opts?.index != null &&
    opts.total != null &&
    opts.total > 1
  ) {
    return `${n} image ${opts.index + 1}`;
  }
  return n;
}

export function fanAvatarAlt(displayName: string | null | undefined): string {
  const n = (displayName || "").trim();
  return n || "Fan";
}

/** Decorative: gradients, spacers, pure chrome. */
export const DECORATIVE_ALT = "";
