import { redirect } from "next/navigation";

/** Canonical route is `/admin/hosts`. */
export default function AdminVerificationsRedirectPage() {
  redirect("/admin/hosts");
}
