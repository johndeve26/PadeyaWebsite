import { permanentRedirect } from "next/navigation";

/** Alias — canonical admin merch moderation lives under /admin/merchandise. */
export default function AdminMerchAliasPage() {
  permanentRedirect("/admin/merchandise");
}
