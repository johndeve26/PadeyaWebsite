import { redirect } from "next/navigation";

export default function LegacyAmbassadorEarningsRedirect() {
  redirect("/dashboard/ambassador/earnings");
}
