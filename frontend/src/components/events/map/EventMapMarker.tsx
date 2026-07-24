/** Marker icon helpers for Google Maps (brand-green pins). */

import { brand } from "@/lib/brand";

export type EventMapMarkerTone = "default" | "selected" | "approximate" | "cluster";

export function eventMapMarkerIcon(opts: {
  tone?: EventMapMarkerTone;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  maps: any;
}) {
  const { tone = "default", maps } = opts;
  const selected = tone === "selected";
  const cluster = tone === "cluster";
  const approx = tone === "approximate";
  const fill = selected
    ? brand.colors.green
    : cluster
      ? brand.colors.paper
      : approx
        ? "#6aad14"
        : brand.colors.green;
  const scale = selected ? 12 : cluster ? 14 : 9;

  return {
    path: maps.SymbolPath.CIRCLE,
    fillColor: fill,
    fillOpacity: selected ? 1 : 0.92,
    strokeColor: brand.colors.ink,
    strokeWeight: selected ? 2.5 : 2,
    scale,
  };
}

export function eventMapMarkerLabel(
  text: string,
  tone: EventMapMarkerTone = "default",
) {
  const cluster = tone === "cluster";
  return {
    text: text.length > 10 ? `${text.slice(0, 9)}…` : text,
    color: brand.colors.ink,
    fontSize: cluster ? "12px" : "10px",
    fontWeight: "700",
  };
}

export function resolveMarkerTone(opts: {
  selected?: boolean;
  approximate?: boolean;
  cluster?: boolean;
}): EventMapMarkerTone {
  if (opts.cluster) return "cluster";
  if (opts.selected) return "selected";
  if (opts.approximate) return "approximate";
  return "default";
}
