import { redirect } from "next/navigation";

/** Admin alias → runtime settings category for host recommendations tuning. */
export default function AdminHostRecommendationsDiscoveryPage() {
  redirect("/admin/settings/runtime/host-recommendations");
}
