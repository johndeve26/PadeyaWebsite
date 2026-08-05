import { getPublicEventBySlug } from "@/lib/public-loaders/entities";
import { buildEventOgImage } from "@/lib/seo/event-og-image";
import {
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-size";

export const alt = "Event on Pàdéyá";
export const size = PROFILE_OG_SIZE;
export const contentType = PROFILE_OG_CONTENT_TYPE;
export const runtime = "nodejs";
export const revalidate = 120;

type Props = { params: Promise<{ slug: string }> };

export default async function EventOpenGraphImage({ params }: Props) {
  const { slug } = await params;
  const event = await getPublicEventBySlug(decodeURIComponent(slug));
  // Missing / private / draft → branded fallback, no private fields.
  return buildEventOgImage(event);
}
