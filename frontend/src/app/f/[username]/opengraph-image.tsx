import { getPublicFanPassport } from "@/lib/public-loaders/entities";
import {
  buildProfileOgImage,
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-image";

export const alt = "Fan Passport profile";
export const size = PROFILE_OG_SIZE;
export const contentType = PROFILE_OG_CONTENT_TYPE;
export const runtime = "nodejs";

type Props = { params: Promise<{ username: string }> };

export default async function FanOpenGraphImage({ params }: Props) {
  const { username } = await params;
  const page = await getPublicFanPassport(decodeURIComponent(username));
  const displayName = page?.display_name?.trim() || "Fan Passport";
  return buildProfileOgImage({
    displayName,
    subtitle: "Fan Passport",
    avatarUrl: page?.avatar_url,
  });
}
