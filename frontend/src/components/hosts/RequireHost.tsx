"use client";

import Link from "next/link";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { Alert, Button, Container, SkeletonLoader } from "@/components/ui";
import { userHasRole } from "@/lib/auth/permissions";
import { PERSONAL_WORKSPACE_SWITCHER_LABEL } from "@/lib/host-access";

/**
 * Allows host owners and accepted team / event staff into host pages.
 * Must be used under HostWorkspaceProvider (host layout).
 */
export function RequireHost({ children }: { children: ReactNode }) {
  const { user, loading, refreshUser } = useAuth();
  const { workspaces, active, loading: wsLoading, error } = useHostWorkspace();

  useEffect(() => {
    if (loading || !user || !active) return;
    if (
      active.is_owner &&
      !userHasRole(user, "host", "host_staff", "super_admin")
    ) {
      void refreshUser();
    }
  }, [loading, user, active, refreshUser]);

  if (loading || wsLoading) {
    return (
      <main className="bg-background py-16 sm:py-20">
        <Container width="narrow" className="space-y-4">
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  if (error) {
    const sessionExpired = /token|authenticated|session/i.test(error);
    return (
      <main className="bg-background py-16 sm:py-20">
        <Container
          width="narrow"
          className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
        >
          <Alert
            tone="danger"
            title={
              sessionExpired
                ? "Session expired"
                : "Host workspace unavailable"
            }
          >
            {sessionExpired
              ? "Sign in again to continue in the host workspace."
              : error}
          </Alert>
          <div className="flex flex-wrap gap-2">
            {sessionExpired ? (
              <Link href={`/login?next=${encodeURIComponent("/host")}`}>
                <Button>Sign in</Button>
              </Link>
            ) : null}
            <Link href="/dashboard">
              <Button variant="ghost">{PERSONAL_WORKSPACE_SWITCHER_LABEL}</Button>
            </Link>
          </div>
        </Container>
      </main>
    );
  }

  if (!active || workspaces.length === 0) {
    return (
      <main className="bg-background py-16 sm:py-20">
        <Container
          width="narrow"
          className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
        >
          <h1 className="text-2xl font-extrabold tracking-tight text-heading">
            Become a host
          </h1>
          <p className="text-muted-foreground">
            Create your host profile before managing events on Pàdéyá — or accept
            a team invite to help another host.
          </p>
          <Link href="/host/onboarding">
            <Button>Start onboarding</Button>
          </Link>
        </Container>
      </main>
    );
  }

  return <>{children}</>;
}
