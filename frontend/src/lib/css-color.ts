import { brand } from "@/lib/brand";

const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

/** Default listing accent when override is blank. */
export const DEFAULT_BRAND_ACCENT = brand.colors.green;

/** Normalize #RGB / #RRGGBB to lowercase #rrggbb. */
export function normalizeHexColor(value: string): string | null {
  const match = value.trim().match(HEX_RE);
  if (!match) return null;
  let hex = match[1]!;
  if (hex.length === 3) {
    hex = hex
      .split("")
      .map((c) => c + c)
      .join("");
  }
  return `#${hex.toLowerCase()}`;
}

function acceptsCssColor(value: string): boolean {
  if (normalizeHexColor(value)) return true;
  if (typeof document === "undefined") {
    return /^[a-zA-Z]+$/.test(value.trim());
  }
  const probe = document.createElement("div");
  probe.style.color = value.trim();
  return probe.style.color !== "";
}

/**
 * Validate and return a storable CSS color string (hex or lowercase name).
 * Empty input returns null (use platform default).
 */
export function normalizeCssColor(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const hex = normalizeHexColor(trimmed);
  if (hex) return hex;
  if (!acceptsCssColor(trimmed)) return null;
  return trimmed.toLowerCase();
}

/** Resolve override to a paintable CSS color for previews and inline styles. */
export function resolveCssColor(
  value: string | null | undefined,
  fallback: string = DEFAULT_BRAND_ACCENT,
): string {
  if (!value?.trim()) return fallback;
  return normalizeCssColor(value) ?? fallback;
}

/** Convert any valid CSS color to #rrggbb for `<input type="color">`. */
export function cssColorToHex(
  value: string,
  fallback: string = DEFAULT_BRAND_ACCENT,
): string {
  const hex = normalizeHexColor(value);
  if (hex) return hex;
  if (typeof document === "undefined") return fallback;

  const canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  const ctx = canvas.getContext("2d");
  if (!ctx) return fallback;

  ctx.fillStyle = value;
  const parsed = ctx.fillStyle;
  if (typeof parsed === "string" && parsed.startsWith("#")) {
    return parsed;
  }

  const rgb = /^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/.exec(parsed);
  if (rgb) {
    const toHex = (n: string) =>
      Number(n).toString(16).padStart(2, "0");
    return `#${toHex(rgb[1]!)}${toHex(rgb[2]!)}${toHex(rgb[3]!)}`;
  }

  return fallback;
}
