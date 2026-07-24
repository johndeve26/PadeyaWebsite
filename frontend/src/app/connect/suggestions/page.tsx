"use client";

import { Suspense } from "react";

import { ConnectShell } from "@/components/fan-connect/ConnectShell";
import { ConnectSuggestions } from "@/components/fan-connect/ConnectSuggestions";
import { SkeletonLoader } from "@/components/ui";

export default function ConnectSuggestionsPage() {
  return (
    <ConnectShell
      title="Shared event energy"
      description="Going to the same events, following the same hosts, and similar scenes — never a dating feed. Turn discovery off anytime in settings."
    >
      <Suspense fallback={<SkeletonLoader className="h-28" />}>
        <ConnectSuggestions />
      </Suspense>
    </ConnectShell>
  );
}
