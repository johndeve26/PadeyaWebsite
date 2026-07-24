"use client";

import Link from "next/link";

import { RoadmapPageContent } from "@/components/host/roadmap/RoadmapPageContent";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button } from "@/components/ui";

export default function HostRoadmapPage() {
  const { active } = useHostWorkspace();

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        operationalHeader
        eyebrow="Launch checklist"
        title="Host roadmap"
        description="Track setup from profile to first published event — statuses are inferred from your workspace data."
        actions={
          <Link href="/host">
            <Button variant="secondary">Command Center</Button>
          </Link>
        }
      >
        <RoadmapPageContent workspace={active} />
      </DashboardShell>
    </RequireHost>
  );
}
