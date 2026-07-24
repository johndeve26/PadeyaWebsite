"use client";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { HostWorkspaceProvider } from "@/components/hosts/HostWorkspaceProvider";
import { WorkspaceSwitcher } from "@/components/hosts/WorkspaceSwitcher";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { PERSONAL_WORKSPACE_TITLE } from "@/lib/host-access";
import { buyerNav, buyerNavGroups } from "@/lib/nav/workspace";

export default function ConnectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RequireAuth>
      <HostWorkspaceProvider>
        <WorkspaceShell
          nav={buyerNav}
          navGroups={buyerNavGroups}
          title={PERSONAL_WORKSPACE_TITLE}
          homeHref="/dashboard"
          toolbar={<WorkspaceSwitcher />}
        >
          {children}
        </WorkspaceShell>
      </HostWorkspaceProvider>
    </RequireAuth>
  );
}
