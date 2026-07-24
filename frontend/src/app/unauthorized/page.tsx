import type { Metadata } from "next";

import { SystemErrorExperience } from "@/components/system/SystemErrorExperience";
import { buildPageMetadata } from "@/lib/seo/site";

export const metadata: Metadata = {
  ...buildPageMetadata({
    title: "Unauthorized",
    description: "You do not have permission to view this page.",
    path: "/unauthorized",
    noIndex: true,
  }),
};

export default function UnauthorizedPage() {
  return (
    <SystemErrorExperience
      code="401"
      title="You don’t have access"
      description="This area needs a different role or permission on Pàdéyá. Switch accounts, open Personal, or contact Support."
      primaryHref="/events"
      primaryLabel="Explore events"
      secondaryHref="/support"
      secondaryLabel="Contact support"
    />
  );
}
