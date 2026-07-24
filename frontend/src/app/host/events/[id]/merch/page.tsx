import { permanentRedirect } from "next/navigation";

/** Legacy path — canonical merchandise studio is `/host/events/[id]/merchandise` (308). */
export default async function LegacyEventMerchRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  permanentRedirect(`/host/events/${id}/merchandise`);
}
