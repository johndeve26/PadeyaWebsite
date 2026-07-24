/** Simple grid clustering for dense map pins (no extra deps). */

import type { MapCluster, MapEventPin, MapLatLng } from "@/lib/maps/types";

function parsePinCoords(pin: MapEventPin): MapLatLng | null {
  if (pin.latitude == null || pin.longitude == null) return null;
  const lat = Number(pin.latitude);
  const lng = Number(pin.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
}

/**
 * Cluster pins into cells sized by zoom.
 * Higher zoom → smaller cells → fewer merges.
 */
export function clusterMapPins(
  pins: MapEventPin[],
  zoom: number,
): { singles: Array<MapEventPin & { position: MapLatLng }>; clusters: MapCluster[] } {
  const cellSize = Math.max(0.01, 0.35 / Math.pow(2, Math.max(0, zoom - 8)));
  const buckets = new Map<
    string,
    { pins: Array<MapEventPin & { position: MapLatLng }>; latSum: number; lngSum: number }
  >();

  for (const pin of pins) {
    const position = parsePinCoords(pin);
    if (!position) continue;
    const key = `${Math.floor(position.lat / cellSize)}:${Math.floor(position.lng / cellSize)}`;
    const bucket = buckets.get(key) ?? { pins: [], latSum: 0, lngSum: 0 };
    bucket.pins.push({ ...pin, position });
    bucket.latSum += position.lat;
    bucket.lngSum += position.lng;
    buckets.set(key, bucket);
  }

  const singles: Array<MapEventPin & { position: MapLatLng }> = [];
  const clusters: MapCluster[] = [];

  for (const [key, bucket] of buckets) {
    if (bucket.pins.length === 1) {
      singles.push(bucket.pins[0]!);
      continue;
    }
    const n = bucket.pins.length;
    clusters.push({
      id: `cluster:${key}`,
      position: { lat: bucket.latSum / n, lng: bucket.lngSum / n },
      count: n,
      eventIds: bucket.pins.map((p) => p.id),
    });
  }

  return { singles, clusters };
}

export function pinCoords(pin: MapEventPin): MapLatLng | null {
  return parsePinCoords(pin);
}
