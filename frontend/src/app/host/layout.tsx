"use client";

import { usePathname } from "next/navigation";
import { useMemo } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { HostAccessGuard } from "@/components/hosts/HostAccessGuard";
import {
  HostWorkspaceProvider,
  useHostWorkspace,
} from "@/components/hosts/HostWorkspaceProvider";
import { WorkspaceSwitcher } from "@/components/hosts/WorkspaceSwitcher";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import {
  hostHomePathForWorkspace,
  hostWorkspaceChromeTitle,
} from "@/lib/host-access";
import { navForWorkspace, navGroupsForWorkspace } from "@/lib/nav/host-nav";

/** Host workspace shell — permission-filtered host nav only (`/host/*`). */
function HostShell({ children }: { children: React.ReactNode }) {
  const { active } = useHostWorkspace();
  const navGroups = useMemo(() => navGroupsForWorkspace(active), [active]);
  const nav = useMemo(() => navForWorkspace(active), [active]);
  const homeHref = useMemo(
    () => (active ? hostHomePathForWorkspace(active) : "/host"),
    [active],
  );

  const title = active?.display_name
    ? hostWorkspaceChromeTitle(active.display_name)
    : "Host";

  return (
    <WorkspaceShell
      nav={nav}
      navGroups={navGroups}
      title={title}
      homeHref={homeHref}
      hostMobileNav
      toolbar={<WorkspaceSwitcher />}
    >
      <HostAccessGuard>{children}</HostAccessGuard>
    </WorkspaceShell>
  );
}

export default function HostLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isOnboarding = pathname?.startsWith("/host/onboarding");
  const isEventPreview = Boolean(
    pathname?.match(/^\/host\/events\/[^/]+\/preview\/?$/),
  );

  return (
    <RequireAuth>
      <HostWorkspaceProvider>
        {isOnboarding || isEventPreview ? (
          children
        ) : (
          <HostShell>{children}</HostShell>
        )}
      </HostWorkspaceProvider>
    </RequireAuth>
  );
}
