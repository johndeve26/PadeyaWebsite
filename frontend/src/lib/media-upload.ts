import { apiUpload } from "@/lib/api";
import { uploadEventMediaFile, uploadHostMediaFile } from "@/lib/events-api";

export type UploadFormImageOptions = {
  eventId?: string;
  mediaType?: string;
  setAsBanner?: boolean;
  /** Prefer account avatar upload (works for fans without a host profile). */
  accountAvatar?: boolean;
  /** Blog media role key — routes to /admin/blog/media/upload */
  blogMediaRole?: string;
};

/** Upload an account profile photo — available to any signed-in user.
 * Applies the photo to Fan Passport (and Host Legacy when present) immediately.
 */
export async function uploadAccountAvatar(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiUpload<{ url: string }>("/users/me/avatar", form);
  return res.url;
}

/**
 * Upload a profile image with fallbacks so fans never need host onboarding.
 * 1) Account avatar endpoint
 * 2) Staging media with media_type=avatar (backend routes fans to account storage)
 */
export async function uploadProfileImage(file: File): Promise<string> {
  try {
    return await uploadAccountAvatar(file);
  } catch (primary) {
    try {
      const staged = await uploadHostMediaFile(file, "avatar");
      return staged.url;
    } catch {
      throw primary;
    }
  }
}

/** Upload an image via host staging, blog media, or event media API; returns a stored URL. */
export async function uploadFormImage(
  file: File,
  options: UploadFormImageOptions = {},
): Promise<string> {
  const mediaType = options.mediaType ?? "other";
  const wantAccountAvatar =
    options.accountAvatar === true ||
    mediaType === "avatar" ||
    mediaType === "logo";

  // Profile photos must never require host onboarding.
  if (wantAccountAvatar) {
    return uploadProfileImage(file);
  }

  if (options.blogMediaRole || mediaType === "blog" || mediaType.startsWith("blog_")) {
    const role =
      options.blogMediaRole ||
      (mediaType.startsWith("blog_") ? mediaType.slice(5) : "inline");
    const { uploadBlogMedia } = await import("@/lib/blog-api");
    const res = await uploadBlogMedia(file, role);
    return res.url;
  }

  if (options.eventId) {
    const updated = await uploadEventMediaFile(options.eventId, file, {
      mediaType,
      setAsBanner: options.setAsBanner,
    });
    if (options.setAsBanner && updated.banner_url) {
      return updated.banner_url;
    }
    if (mediaType === "mobile_banner" && updated.mobile_banner_url) {
      return updated.mobile_banner_url;
    }
    if (mediaType === "social_share" && updated.social_share_image_url) {
      return updated.social_share_image_url;
    }
    const match = [...(updated.media ?? [])]
      .reverse()
      .find((m) => m.media_type === mediaType);
    if (match?.url) return match.url;
    throw new Error("Upload succeeded but no URL was returned");
  }

  // Backend routes non-host avatar/logo/other profile uploads to account storage.
  const staged = await uploadHostMediaFile(file, mediaType);
  return staged.url;
}

export function splitImageUrlLines(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((line) => line.trim())
    .filter(Boolean);
}
