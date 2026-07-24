import { redirect } from "next/navigation";

/** Host workspace Help — Host-oriented Help Center. */
export default function HostHelpPage() {
  redirect("/help?audience=host");
}
