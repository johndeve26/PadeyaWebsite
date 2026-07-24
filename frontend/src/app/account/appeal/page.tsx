import type { Metadata } from "next";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { SuspendedAccountPage } from "@/components/account/SuspendedAccountPage";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = {
  ...buildPageMetadata({
    title: "Appeal suspension",
    description: "Submit an appeal for a suspended or restricted Pàdéyá account.",
    path: "/account/appeal",
    noIndex: true,
  }),
};

export default function AccountAppealPage() {
  return (
    <RequireAuth>
      <SuspendedAccountPage />
    </RequireAuth>
  );
}
