import HostOpenGraphImage from "./opengraph-image";
import {
  PROFILE_OG_CONTENT_TYPE,
  PROFILE_OG_SIZE,
} from "@/lib/seo/profile-og-size";

export const alt = "Host Legacy profile on Pàdéyá";
export const size = PROFILE_OG_SIZE;
export const contentType = PROFILE_OG_CONTENT_TYPE;
export const runtime = "nodejs";
export const revalidate = 120;

export default HostOpenGraphImage;
