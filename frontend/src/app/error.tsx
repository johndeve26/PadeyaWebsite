"use client";

import { useEffect } from "react";

import { SystemErrorExperience } from "@/components/system/SystemErrorExperience";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[padeya:route-error]", error.digest || error.message);
  }, [error]);

  return (
    <div>
      <SystemErrorExperience
        code="Error"
        title="Something went wrong"
        description="This page hit an unexpected error. You can try again, or head home and continue from there."
        primaryHref="/"
        primaryLabel="Back to home"
        secondaryHref="/support"
        secondaryLabel="Contact support"
      />
      <div className="flex justify-center pb-12">
        <button
          type="button"
          onClick={() => reset()}
          className="text-sm font-semibold text-primary hover:underline"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
