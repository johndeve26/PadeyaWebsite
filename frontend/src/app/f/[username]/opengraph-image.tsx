import { getPublicFanPassport } from "@/lib/public-loaders/entities";
import { buildFanPassportOgImage } from "@/lib/seo/fan-og-image";
import {
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-size";

export const alt = "Fan Passport on Pàdéyá";
export const size = PROFILE_OG_SIZE;
export const contentType = PROFILE_OG_CONTENT_TYPE;
export const runtime = "nodejs";
/** Align with public fan loader freshness; avoid indefinitely stale cards. */
export const revalidate = 120;

type Props = { params: Promise<{ username: string }> };

export default async function FanOpenGraphImage({ params }: Props) {
  const { username } = await params;
  const page = await getPublicFanPassport(decodeURIComponent(username));
  // Private / missing / suspended → branded fallback, no private fields.
  return buildFanPassportOgImage(page);
}
