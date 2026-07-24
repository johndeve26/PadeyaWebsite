import {
  LocationHubPage,
  locationHubMetadata,
} from "@/lib/discovery/location-hub-page";

type Props = { params: Promise<{ countrySlug: string }> };

export async function generateMetadata({ params }: Props) {
  const { countrySlug } = await params;
  return locationHubMetadata("country", countrySlug);
}

export default async function CountryHubPage({ params }: Props) {
  const { countrySlug } = await params;
  return (
    <LocationHubPage
      kind="country"
      slug={countrySlug}
      hubKind="country"
    />
  );
}
