import { getPublicLegacyByUsername } from "@/lib/public-loaders/entities";
import {
  buildProfileOgImage,
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-image";

export const alt = "Host profile";
export const size = PROFILE_OG_SIZE;
export const contentType = PROFILE_OG_CONTENT_TYPE;
export const runtime = "nodejs";

type Props = { params: Promise<{ username: string }> };

export default async function HostOpenGraphImage({ params }: Props) {
  const { username } = await params;
  const page = await getPublicLegacyByUsername(decodeURIComponent(username));
  const displayName = page?.display_name?.trim() || "Host";
  // Prefer DP (avatar) over cover — matches Fan Passport share behaviour.
  return buildProfileOgImage({
    displayName,
    subtitle: "Host on Pàdéyá",
    avatarUrl: page?.profile?.avatar_url,
  });
}
