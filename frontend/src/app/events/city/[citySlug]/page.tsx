import {
  LocationHubPage,
  locationHubMetadata,
} from "@/lib/discovery/location-hub-page";

type Props = { params: Promise<{ citySlug: string }> };

export async function generateMetadata({ params }: Props) {
  const { citySlug } = await params;
  return locationHubMetadata("city", citySlug);
}

export default async function CityHubPage({ params }: Props) {
  const { citySlug } = await params;
  return <LocationHubPage kind="city" slug={citySlug} hubKind="city" />;
}
