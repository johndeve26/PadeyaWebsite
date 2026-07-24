"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Button, SectionHeader, WorkspaceNavGrid } from "@/components/ui";
import { userHasPermission } from "@/lib/auth/permissions";

const ALL_PLATFORM_ITEMS = [
  {
    href: "/admin/platform/go-live",
    title: "Go live",
    description:
      "Production preflight — environment, demo data, Paystack, email, migrations. Read-only.",
    meta: "Deploy",
    permissions: ["admin.platform.view_readiness", "admin.full_access"] as const,
  },
  {
    href: "/admin/platform/maintenance",
    title: "Maintenance",
    description:
      "Full-site or section maintenance modes, schedules, and bypass for trusted admins.",
    meta: "Operations",
    permissions: [
      "admin.maintenance.view",
      "admin.maintenance.manage",
      "admin.full_access",
    ] as const,
  },
  {
    href: "/admin/platform/maintenance/history",
    title: "Maintenance history",
    description: "Audit trail of maintenance mode changes and schedules.",
    meta: "Audit",
    permissions: ["admin.maintenance.view", "admin.full_access"] as const,
  },
  {
    href: "/admin/platform/maintenance/notifications",
    title: "Maintenance notifications",
    description: "Advance notices and test sends before planned downtime.",
    meta: "Comms",
    permissions: [
      "admin.maintenance.notify",
      "admin.maintenance.manage",
      "admin.full_access",
    ] as const,
  },
];

export default function AdminPlatformHubPage() {
  const { user } = useAuth();
  const items = ALL_PLATFORM_ITEMS.filter((item) =>
    userHasPermission(user, ...item.permissions),
  ).map(({ permissions: _p, ...rest }) => rest);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Platform"
      title="Platform operations"
      description="Go-live checks, maintenance windows, and production safety for Pàdéyá — no fan or host tools here."
      actions={
        <Link href="/admin">
          <Button variant="secondary" size="sm">
            Admin home
          </Button>
        </Link>
      }
    >
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          You don’t have permission to view platform operations. Ask a super admin for{" "}
          <span className="font-mono text-xs">admin.platform.view_readiness</span> or{" "}
          <span className="font-mono text-xs">admin.maintenance.view</span>.
        </p>
      ) : (
        <>
          <SectionHeader
            eyebrow="Platform"
            title="Choose a workspace"
            description="Preflight before launch, then use maintenance when you need controlled downtime."
          />
          <WorkspaceNavGrid items={items} />
        </>
      )}
    </DashboardShell>
  );
}
