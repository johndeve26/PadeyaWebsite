"use client";

import type { ReactNode } from "react";

import { HostPermissionDenied } from "@/components/hosts/HostPermissionDenied";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHost } from "@/components/hosts/RequireHost";
import { Container, SkeletonLoader } from "@/components/ui";

/** Host-owner-only surfaces (payouts, bank). */
export function RequireHostOwner({ children }: { children: ReactNode }) {
  const { active, loading, isOwner } = useHostWorkspace();

  return (
    <RequireHost>
      {loading || !active ? (
        <main className="bg-background py-16 sm:py-20">
          <Container width="narrow" className="space-y-4">
            <SkeletonLoader lines={4} />
          </Container>
        </main>
      ) : !isOwner ? (
        <HostPermissionDenied />
      ) : (
        children
      )}
    </RequireHost>
  );
}
