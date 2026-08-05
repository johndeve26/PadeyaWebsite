/**
 * Dynamic event-title sizing for 1200×630 Open Graph cards.
 * Estimates visual width with weighted characters and balances line breaks.
 */

export type EventTitleFit = {
  fontSize: number;
  lines: string[];
  maxLines: number;
  lineHeight: number;
  letterSpacing: number;
  truncated: boolean;
  /** Layout hint derived from title length / fit. */
  density: "short" | "medium" | "long" | "very-long";
};

const TITLE_FONT_SIZES = [96, 88, 80, 72, 64, 58, 52, 46, 42, 38] as const;
const MIN_FONT = 38;

export function getCharacterWeight(character: string): number {
  if (/[MWQO@%]/.test(character)) return 1.35;
  if (/[A-Z]/.test(character)) return 1.1;
  if (/[ilI1.,'|]/.test(character)) return 0.5;
  if (/\s/.test(character)) return 0.45;
  return 1;
}

export function estimateTextWidth(text: string, fontSize: number): number {
  let units = 0;
  for (const ch of text) units += getCharacterWeight(ch);
  // ~0.56em average for sans-serif at weight 800
  return units * fontSize * 0.56;
}

function densityForLength(len: number): EventTitleFit["density"] {
  if (len <= 22) return "short";
  if (len <= 38) return "medium";
  if (len <= 80) return "long";
  return "very-long";
}

function maxLinesFor(
  density: EventTitleFit["density"],
  opts: { hasTagline: boolean; hasFlyerSide: boolean },
): number {
  if (density === "short") return 2;
  if (density === "medium") return 2;
  if (density === "long") return opts.hasTagline ? 2 : 3;
  return opts.hasFlyerSide ? 3 : 4;
}

/** Greedy wrap that prefers balanced line lengths. */
export function wrapTitleLines(
  title: string,
  fontSize: number,
  maxWidth: number,
  maxLines: number,
): { lines: string[]; truncated: boolean } {
  const words = title.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return { lines: [""], truncated: false };

  const lines: string[] = [];
  let current = "";
  let truncated = false;

  const pushCurrent = () => {
    if (current) lines.push(current);
    current = "";
  };

  for (let wi = 0; wi < words.length; wi++) {
    const word = words[wi]!;
    const candidate = current ? `${current} ${word}` : word;
    if (estimateTextWidth(candidate, fontSize) <= maxWidth) {
      current = candidate;
      continue;
    }
    if (!current) {
      // Exceptionally long unbroken word — hard truncate.
      let cut = word;
      while (
        cut.length > 1 &&
        estimateTextWidth(`${cut}…`, fontSize) > maxWidth
      ) {
        cut = cut.slice(0, -1);
      }
      lines.push(`${cut}…`);
      truncated = true;
      current = "";
      if (lines.length >= maxLines) {
        return { lines: lines.slice(0, maxLines), truncated: true };
      }
      continue;
    }
    pushCurrent();
    if (lines.length >= maxLines) {
      const rest = words.slice(wi).join(" ");
      const last = lines[lines.length - 1]!;
      let merged = `${last} ${rest}`;
      while (
        merged.length > 1 &&
        estimateTextWidth(`${merged}…`, fontSize) > maxWidth
      ) {
        merged = merged.slice(0, -1).trimEnd();
      }
      lines[lines.length - 1] = `${merged}…`;
      return { lines, truncated: true };
    }
    current = word;
  }
  pushCurrent();

  // Rebalance 2-line splits when first line is very short.
  if (!truncated && lines.length === 2) {
    const [a, b] = lines;
    const all = `${a} ${b}`.split(/\s+/);
    if (a!.split(/\s+/).length === 1 && all.length >= 4) {
      const mid = Math.ceil(all.length / 2);
      const left = all.slice(0, mid).join(" ");
      const right = all.slice(mid).join(" ");
      if (
        estimateTextWidth(left, fontSize) <= maxWidth &&
        estimateTextWidth(right, fontSize) <= maxWidth
      ) {
        return { lines: [left, right], truncated: false };
      }
    }
  }

  return { lines: lines.slice(0, maxLines), truncated };
}

export function fitEventTitle(
  title: string,
  availableWidth: number,
  availableHeight: number,
  opts: { hasTagline?: boolean; hasFlyerSide?: boolean } = {},
): EventTitleFit {
  const raw = title.trim().replace(/\s+/g, " ") || "Event";
  const density = densityForLength(raw.length);
  const hasTagline = Boolean(opts.hasTagline);
  const hasFlyerSide = Boolean(opts.hasFlyerSide);
  const maxLines = maxLinesFor(density, { hasTagline, hasFlyerSide });
  const lineHeightRatio = 1.08;

  for (const fontSize of TITLE_FONT_SIZES) {
    if (fontSize < MIN_FONT) break;
    const { lines, truncated } = wrapTitleLines(
      raw,
      fontSize,
      availableWidth,
      maxLines,
    );
    const blockHeight = lines.length * fontSize * lineHeightRatio;
    const widest = Math.max(
      ...lines.map((l) => estimateTextWidth(l, fontSize)),
      0,
    );
    if (
      !truncated &&
      blockHeight <= availableHeight &&
      widest <= availableWidth + 2
    ) {
      return {
        fontSize,
        lines,
        maxLines,
        lineHeight: lineHeightRatio,
        letterSpacing: fontSize >= 72 ? -1.6 : fontSize >= 52 ? -1.1 : -0.6,
        truncated,
        density,
      };
    }
  }

  // Absolute minimum — force fit with truncation.
  const fontSize = MIN_FONT;
  const { lines } = wrapTitleLines(raw, fontSize, availableWidth, maxLines);
  return {
    fontSize,
    lines,
    maxLines,
    lineHeight: lineHeightRatio,
    letterSpacing: -0.5,
    truncated: true,
    density: "very-long",
  };
}
