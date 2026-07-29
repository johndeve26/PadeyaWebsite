"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { fetchAdminTeamRoles, type AdminTeamRole } from "@/lib/admin-team/api";
import { ApiError } from "@/lib/api";

export default function AdminTeamRolesPage() {
  const toast = useToast();
  const [roles, setRoles] = useState<AdminTeamRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      void (async () => {
        try {
          const data = await fetchAdminTeamRoles();
          if (!cancelled) setRoles(data.roles);
        } catch (err) {
          const message =
            err instanceof ApiError ? err.message : "Failed to load roles";
          if (!cancelled) {
            setError(message);
            toast.push({
              title: "Could not load roles",
              description: message,
              tone: "danger",
            });
          }
        } finally {
          if (!cancelled) setLoading(false);
        }
      })();
    });
    return () => {
      cancelled = true;
    };
  }, [toast]);

  const systemRoles = roles.filter((r) => r.is_system);
  const customRoles = roles.filter((r) => !r.is_system);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Team"
      title="Roles"
      description="Create custom roles and tick individual features. System presets are read-only — duplicate them to customize."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/team">
            <Button variant="secondary" size="sm">
              Team
            </Button>
          </Link>
          <Link href="/admin/team/roles/new">
            <Button size="sm">New custom role</Button>
          </Link>
        </div>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {loading ? (
        <SkeletonLoader lines={6} />
      ) : roles.length === 0 ? (
        <EmptyState
          title="No roles"
          description="Create a custom role or wait for system roles to seed."
        />
      ) : (
        <div className="space-y-8">
          <section className="space-y-4">
            <SectionHeader
              title="Custom roles"
              description="Editable — tick or untick individual features per role."
            />
            {customRoles.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No custom roles yet.{" "}
                <Link href="/admin/team/roles/new" className="text-primary underline">
                  Create one
                </Link>{" "}
                or duplicate a system role.
              </p>
            ) : (
              <ul className="divide-y divide-border border-y border-border">
                {customRoles.map((role) => (
                  <RoleRow key={role.id} role={role} href={`/admin/team/roles/${role.id}`} action="Edit features" />
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-4">
            <SectionHeader
              title="System roles"
              description="Fixed presets. Open to review features, or duplicate as a custom role to change them."
            />
            <ul className="divide-y divide-border border-y border-border">
              {systemRoles.map((role) => (
                <RoleRow
                  key={role.id}
                  role={role}
                  href={`/admin/team/roles/${role.id}`}
                  action="View / duplicate"
                />
              ))}
            </ul>
          </section>
        </div>
      )}
    </DashboardShell>
  );
}

function RoleRow({
  role,
  href,
  action,
}: {
  role: AdminTeamRole;
  href: string;
  action: string;
}) {
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 py-4">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <p className="font-semibold text-heading">{role.name}</p>
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {role.is_system ? "System" : "Custom"}
            {role.is_high_level ? " · High-level" : ""}
          </span>
        </div>
        {role.description ? (
          <p className="text-sm text-muted-foreground">{role.description}</p>
        ) : null}
        <p className="text-xs text-muted-foreground">
          {role.permission_codes.length} feature
          {role.permission_codes.length === 1 ? "" : "s"}
          {role.system_key ? ` · ${role.system_key}` : ""}
        </p>
      </div>
      <Link href={href}>
        <Button size="sm" variant={role.is_system ? "secondary" : "primary"}>
          {action}
        </Button>
      </Link>
    </li>
  );
}
