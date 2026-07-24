import { redirect } from "next/navigation";

/** Avoid /hosts/recommendations being treated as a host slug. */
export default function HostsRecommendationsRedirectPage() {
  redirect("/hosts?sort=recommended");
}
