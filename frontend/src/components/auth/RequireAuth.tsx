"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { SuspendedAccountPage } from "@/components/account/SuspendedAccountPage";
import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Container, SkeletonLoader } from "@/components/ui";
import { userHasRole } from "@/lib/auth/permissions";

type RequireAuthProps = {
  children: ReactNode;
  roles?: string[];
  /** When true, deny access while an impersonation session is active. */
  denyWhileImpersonating?: boolean;
};

export function RequireAuth({
  children,
  roles,
  denyWhileImpersonating = false,
}: RequireAuthProps) {
  const { user, loading, authInitialized, isImpersonating } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (authInitialized && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [authInitialized, user, router, pathname]);

  if (!authInitialized || loading) {
    return (
      <main className="bg-background py-16 sm:py-20">
        <Container width="narrow" className="space-y-4">
          <SkeletonLoader lines={5} />
        </Container>
      </main>
    );
  }

  if (!user) {
    return null;
  }

  if (denyWhileImpersonating && isImpersonating) {
    return (
      <main className="bg-background py-20">
        <Container
          width="narrow"
          className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
        >
          <h1 className="text-2xl font-bold text-heading">
            Admin unavailable while impersonating
          </h1>
          <p className="text-muted-foreground">
            You are viewing Pàdéyá as another user. Exit impersonation to return to
            admin tools. Admin permissions do not apply in this session.
          </p>
          <Link href="/dashboard">
            <Button variant="dark">Go to dashboard</Button>
          </Link>
        </Container>
      </main>
    );
  }

  const accountStatus = (user.account_status || "").toLowerCase();
  if (
    accountStatus === "suspended" ||
    accountStatus === "banned" ||
    user.is_active === false
  ) {
    if (accountStatus === "banned") {
      return (
        <main className="bg-background py-16 sm:py-20">
          <Container
            width="narrow"
            className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
          >
            <h1 className="text-2xl font-bold text-heading">Account banned</h1>
            <p className="text-muted-foreground">
              This account is not available. Contact support if you need help.
            </p>
            <Link href="/">
              <Button variant="secondary">Back to home</Button>
            </Link>
          </Container>
        </main>
      );
    }
    // Dedicated route renders children (SuspendedAccountPage) to avoid nesting.
    if (pathname.startsWith("/account/suspended")) {
      return <>{children}</>;
    }
    return <SuspendedAccountPage />;
  }

  if (roles && !userHasRole(user, ...roles)) {
    return (
      <main className="bg-background py-20">
        <Container width="narrow" className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
          <h1 className="text-2xl font-bold text-heading">Access denied</h1>
          <p className="text-muted-foreground">
            Your account does not have permission to view this area.
          </p>
          <Link href="/dashboard">
            <Button variant="dark">Go to dashboard</Button>
          </Link>
        </Container>
      </main>
    );
  }

  return <>{children}</>;
}
