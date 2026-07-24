"use client";

import { Suspense } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { MessagesInbox } from "@/components/messaging/MessagesInbox";
import { MessagesViewportFrame } from "@/components/messaging/MessagesViewportFrame";
import { SkeletonLoader } from "@/components/ui";

export default function HostMessageThreadPage() {
  return (
    <DashboardShell tone="soft" hideHeader fillViewport>
      <MessagesViewportFrame>
        <Suspense fallback={<SkeletonLoader lines={6} />}>
          <MessagesInbox mode="host" basePath="/host/messages" />
        </Suspense>
      </MessagesViewportFrame>
    </DashboardShell>
  );
}
