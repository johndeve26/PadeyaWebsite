import { apiUpload } from "@/lib/api";
import { uploadEventMediaFile, uploadHostMediaFile } from "@/lib/events-api";

export type UploadFormImageOptions = {
  eventId?: string;
  mediaType?: string;
  setAsBanner?: boolean;
  /** Prefer account avatar upload (works for fans without a host profile). */
  accountAvatar?: boolean;
};

/** Upload an account profile photo — available to any signed-in user. */
export async function uploadAccountAvatar(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiUpload<{ url: string }>("/users/me/avatar", form);
  return res.url;
}

/** Upload an image via host staging or event media API; returns a stored URL. */
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
    return uploadAccountAvatar(file);
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

  const staged = await uploadHostMediaFile(file, mediaType);
  return staged.url;
}

export function splitImageUrlLines(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((line) => line.trim())
    .filter(Boolean);
}
