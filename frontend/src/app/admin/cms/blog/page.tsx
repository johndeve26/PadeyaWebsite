import { redirect } from "next/navigation";

export default function CmsBlogRedirect() {
  redirect("/admin/blog");
}
