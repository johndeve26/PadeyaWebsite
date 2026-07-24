"use client";

import { Suspense } from "react";

import { SupportGuidedFlowPage } from "@/components/support/SupportGuidedFlow";
import { SkeletonLoader } from "@/components/ui";

export default function SupportCenterLandingPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-3xl px-4 py-16">
          <SkeletonLoader lines={8} />
        </div>
      }
    >
      <SupportGuidedFlowPage />
    </Suspense>
  );
}
