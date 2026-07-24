/** Shared map types — provider-agnostic so Mapbox/Leaflet can swap later. */

export type MapLatLng = { lat: number; lng: number };

export type MapBounds = {
  north: number;
  south: number;
  east: number;
  west: number;
};

export type MapEventPin = {
  id: string;
  slug: string;
  title: string;
  banner_url?: string | null;
  start_datetime: string;
  end_datetime?: string | null;
  price_label: string;
  min_price?: number | null;
  is_free?: boolean;
  category_name?: string | null;
  category_slug?: string | null;
  host_display_name?: string | null;
  public_location_label?: string | null;
  city?: string | null;
  area?: string | null;
  latitude: string | null;
  longitude: string | null;
  location_visibility?: string;
  location_map_mode?: "exact" | "approximate" | "none" | string;
  location_privacy_message?: string | null;
  distance_km?: number | null;
  distance_label?: string | null;
  distance_is_approximate?: boolean;
};

export type MapMarkerInput = {
  id: string;
  position: MapLatLng;
  label?: string;
  selected?: boolean;
  approximate?: boolean;
};

export type MapCluster = {
  id: string;
  position: MapLatLng;
  count: number;
  eventIds: string[];
};

export type MapProviderKind = "google" | "none";

export type MapViewport = {
  center: MapLatLng;
  zoom: number;
  bounds: MapBounds | null;
};
