import { redirect } from "next/navigation";

/** Alias: Featured Placement Slots live under /admin/featured-placements. */
export default function AdminEventsFeaturedRedirect() {
  redirect("/admin/featured-placements");
}
