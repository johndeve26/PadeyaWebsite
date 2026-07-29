"use client";

import { useMemo } from "react";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { HostWorkspaceProvider } from "@/components/hosts/HostWorkspaceProvider";
import { SponsorWorkspaceProvider } from "@/components/sponsor/SponsorWorkspaceProvider";
import { WorkspaceSwitcher } from "@/components/hosts/WorkspaceSwitcher";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { ADMIN_PANEL_ROLES } from "@/lib/auth/workspace-access";
import { navForAdmin, navGroupsForAdmin } from "@/lib/nav/admin-nav";

function AdminShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const nav = useMemo(() => navForAdmin(user), [user]);
  const navGroups = useMemo(() => navGroupsForAdmin(user), [user]);

  return (
    <HostWorkspaceProvider>
      <SponsorWorkspaceProvider>
      <WorkspaceShell
        nav={nav}
        navGroups={navGroups}
        title="Admin"
        homeHref="/admin"
        toolbar={<WorkspaceSwitcher />}
      >
        {children}
      </WorkspaceShell>
      </SponsorWorkspaceProvider>
    </HostWorkspaceProvider>
  );
}

export default function AdminLayoutClient({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname() || "";
  // Pending invitees are not admins yet — skip panel roles and allow
  // unauthenticated preview (sign-in CTAs live on the accept page).
  const isInviteAccept = pathname.startsWith("/admin/team/invites/");

  if (isInviteAccept) {
    return <>{children}</>;
  }

  return (
    <RequireAuth
      roles={[...ADMIN_PANEL_ROLES]}
      denyWhileImpersonating
    >
      <AdminShell>{children}</AdminShell>
    </RequireAuth>
  );
}
