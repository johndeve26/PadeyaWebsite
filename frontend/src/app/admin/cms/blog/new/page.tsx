import { redirect } from "next/navigation";

export default function CmsBlogNewRedirect() {
  redirect("/admin/blog/new");
}
