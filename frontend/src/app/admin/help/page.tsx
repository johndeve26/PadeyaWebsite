import { redirect } from "next/navigation";

/** Admin Help entry — Admin-oriented Help Center. */
export default function AdminHelpPage() {
  redirect("/help?audience=admin");
}
