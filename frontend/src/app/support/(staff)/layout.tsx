"use client";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { HostWorkspaceProvider } from "@/components/hosts/HostWorkspaceProvider";
import { WorkspaceSwitcher } from "@/components/hosts/WorkspaceSwitcher";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { SUPPORT_DESK_ROLES } from "@/lib/auth/workspace-access";
import { supportNav } from "@/lib/nav/workspace";

export default function SupportStaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RequireAuth roles={[...SUPPORT_DESK_ROLES]}>
      <HostWorkspaceProvider>
        <WorkspaceShell
          nav={supportNav}
          title="Support"
          homeHref="/support/desk"
          toolbar={<WorkspaceSwitcher />}
        >
          {children}
        </WorkspaceShell>
      </HostWorkspaceProvider>
    </RequireAuth>
  );
}
