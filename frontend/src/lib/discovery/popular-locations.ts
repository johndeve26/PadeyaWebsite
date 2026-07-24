import type { LocationKind } from "@/lib/taxonomy-api";

/** Curated popular shortcuts for the /events location filter. */
export const POPULAR_LOCATION_SHORTCUTS: {
  kind: LocationKind;
  slug: string;
  label: string;
}[] = [
  { kind: "city", slug: "lagos", label: "Lagos" },
  { kind: "city", slug: "ibadan", label: "Ibadan" },
  { kind: "city", slug: "abuja", label: "Abuja" },
  { kind: "city", slug: "akure", label: "Akure" },
  { kind: "area", slug: "victoria-island", label: "Victoria Island" },
  { kind: "area", slug: "lekki", label: "Lekki" },
  { kind: "area", slug: "ikeja", label: "Ikeja" },
  { kind: "area", slug: "yaba", label: "Yaba" },
  { kind: "area", slug: "mainland", label: "Lagos Mainland" },
];
