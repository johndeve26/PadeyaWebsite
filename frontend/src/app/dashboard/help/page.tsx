import { redirect } from "next/navigation";

/** Buyer dashboard Help — Fan-oriented Help Center. */
export default function DashboardHelpPage() {
  redirect("/help?audience=fan");
}
