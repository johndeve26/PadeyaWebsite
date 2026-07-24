import { redirect } from "next/navigation";

/** @deprecated Use /admin/platform/go-live */
export default function AdminPlatformReadinessRedirectPage() {
  redirect("/admin/platform/go-live");
}
