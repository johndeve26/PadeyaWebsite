import {
  LocationHubPage,
  locationHubMetadata,
} from "@/lib/discovery/location-hub-page";

type Props = { params: Promise<{ stateSlug: string }> };

export async function generateMetadata({ params }: Props) {
  const { stateSlug } = await params;
  return locationHubMetadata("state", stateSlug);
}

export default async function StateHubPage({ params }: Props) {
  const { stateSlug } = await params;
  return <LocationHubPage kind="state" slug={stateSlug} hubKind="state" />;
}
