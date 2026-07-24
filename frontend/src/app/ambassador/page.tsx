import { redirect } from "next/navigation";

export default function LegacyAmbassadorRedirect() {
  redirect("/dashboard/ambassador");
}
