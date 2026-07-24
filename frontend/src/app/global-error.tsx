"use client";

import { useEffect } from "react";

import { SystemErrorExperience } from "@/components/system/SystemErrorExperience";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[padeya:global-error]", error.digest || error.message);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <SystemErrorExperience
          ink
          code="500"
          title="Pàdéyá needs a moment"
          description="A fatal application error occurred. Please reload or return home. If it keeps happening, contact Support."
          primaryHref="/"
          primaryLabel="Back to home"
          secondaryHref="/support"
          secondaryLabel="Contact support"
        />
        <div className="fixed bottom-6 left-0 right-0 flex justify-center">
          <button
            type="button"
            onClick={() => reset()}
            className="rounded-full border border-paper/30 px-4 py-2 text-sm font-semibold text-paper hover:border-primary hover:text-primary"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
