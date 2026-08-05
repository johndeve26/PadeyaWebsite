import { getPublicLegacyByUsername } from "@/lib/public-loaders/entities";
import { buildHostLegacyOgImage } from "@/lib/seo/host-og-image";
import {
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-size";

export const alt = "Host Legacy profile on Pàdéyá";
export const size = PROFILE_OG_SIZE;
export const contentType = PROFILE_OG_CONTENT_TYPE;
export const runtime = "nodejs";
/** Align with public Legacy ISR (`page.tsx` revalidate = 120). */
export const revalidate = 120;

type Props = { params: Promise<{ username: string }> };

export default async function HostOpenGraphImage({ params }: Props) {
  const { username } = await params;
  const page = await getPublicLegacyByUsername(decodeURIComponent(username));
  // Missing / inactive / private hosts: branded fallback, no private fields.
  return buildHostLegacyOgImage(page);
}
