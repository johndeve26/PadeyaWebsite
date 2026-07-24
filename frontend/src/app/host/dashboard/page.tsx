import { permanentRedirect } from "next/navigation";

/** Defensive alias — canonical Host Command Center is `/host`. */
export default function HostDashboardAliasPage() {
  permanentRedirect("/host");
}
