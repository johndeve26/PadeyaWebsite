/** Marker for full-bleed dark tops the marketing header can sit over. */
export const HEADER_DARK_SURFACE = "dark" as const;

export const headerDarkSurfaceProps = {
  "data-header-surface": HEADER_DARK_SURFACE,
} as const;
