"use client";

import type { ReactNode } from "react";

import { HostPermissionDenied } from "@/components/hosts/HostPermissionDenied";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHost } from "@/components/hosts/RequireHost";
import { Container, SkeletonLoader } from "@/components/ui";
import { hasHostPermission } from "@/lib/host-access";

/** Owner or team member with any team.* permission. */
export function RequireHostTeamManage({ children }: { children: ReactNode }) {
  const { active, loading, isOwner } = useHostWorkspace();
  const allowed = Boolean(
    isOwner ||
      hasHostPermission(
        active,
        "team.view",
        "team.invite",
        "team.edit_permissions",
        "team.remove_members",
      ),
  );

  return (
    <RequireHost>
      {loading || !active ? (
        <main className="bg-background py-16 sm:py-20">
          <Container width="narrow" className="space-y-4">
            <SkeletonLoader lines={4} />
          </Container>
        </main>
      ) : !allowed ? (
        <HostPermissionDenied />
      ) : (
        children
      )}
    </RequireHost>
  );
}
