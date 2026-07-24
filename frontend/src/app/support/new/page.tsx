"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { SkeletonLoader } from "@/components/ui";

function RedirectInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const category = searchParams.get("category");
    const href = category
      ? `/support?topic=${encodeURIComponent(category)}`
      : "/support";
    router.replace(href);
  }, [router, searchParams]);

  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <SkeletonLoader lines={4} />
      <p className="mt-4 text-sm text-muted-foreground">
        Taking you to guided Support…
      </p>
    </div>
  );
}

/** Legacy /support/new → guided Support (Help first). */
export default function SupportNewTicketRedirectPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-lg px-4 py-16">
          <SkeletonLoader lines={4} />
        </div>
      }
    >
      <RedirectInner />
    </Suspense>
  );
}
