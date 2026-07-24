"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { HostWorkspaceProvider } from "@/components/hosts/HostWorkspaceProvider";
import { WorkspaceSwitcher } from "@/components/hosts/WorkspaceSwitcher";
import {
  SponsorWorkspaceProvider,
  useSponsorWorkspace,
} from "@/components/sponsor/SponsorWorkspaceProvider";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { flatSponsorNav, sponsorNavGroups } from "@/lib/nav/sponsor-nav";

function SponsorAccessGuard({ children }: { children: React.ReactNode }) {
  const { workspaces, loading } = useSponsorWorkspace();
  const router = useRouter();
  const pathname = usePathname();
  const isBareRoute =
    pathname?.startsWith("/sponsor/create") ||
    pathname?.startsWith("/sponsor/team/invite");

  useEffect(() => {
    if (loading || isBareRoute) return;
    if (workspaces.length === 0) {
      router.replace("/sponsor/create");
    }
  }, [loading, workspaces.length, isBareRoute, router]);

  if (loading) {
    return (
      <p className="text-sm text-muted-foreground">Loading sponsor workspace…</p>
    );
  }
  if (!isBareRoute && workspaces.length === 0) {
    return null;
  }
  return children;
}

function SponsorShell({ children }: { children: React.ReactNode }) {
  const { active } = useSponsorWorkspace();
  const title = active?.display_name
    ? `${active.display_name} · Sponsor`
    : "Sponsor";

  return (
    <WorkspaceShell
      nav={flatSponsorNav()}
      navGroups={sponsorNavGroups()}
      title={title}
      homeHref="/sponsor"
      toolbar={<WorkspaceSwitcher />}
    >
      <SponsorAccessGuard>{children}</SponsorAccessGuard>
    </WorkspaceShell>
  );
}

export default function SponsorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isBareRoute =
    pathname?.startsWith("/sponsor/create") ||
    pathname?.startsWith("/sponsor/team/invite");

  return (
    <RequireAuth>
      <HostWorkspaceProvider>
        <SponsorWorkspaceProvider>
          {isBareRoute ? (
            children
          ) : (
            <SponsorShell>{children}</SponsorShell>
          )}
        </SponsorWorkspaceProvider>
      </HostWorkspaceProvider>
    </RequireAuth>
  );
}
