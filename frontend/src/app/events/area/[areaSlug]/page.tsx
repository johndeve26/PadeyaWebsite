import {
  LocationHubPage,
  locationHubMetadata,
} from "@/lib/discovery/location-hub-page";

type Props = { params: Promise<{ areaSlug: string }> };

export async function generateMetadata({ params }: Props) {
  const { areaSlug } = await params;
  return locationHubMetadata("area", areaSlug);
}

export default async function AreaHubPage({ params }: Props) {
  const { areaSlug } = await params;
  return <LocationHubPage kind="area" slug={areaSlug} hubKind="area" />;
}
