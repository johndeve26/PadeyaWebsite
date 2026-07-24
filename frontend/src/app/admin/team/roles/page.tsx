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

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Team"
      title="Roles"
      description="System teams and custom roles with selected permissions."
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
        <div className="space-y-6">
          <SectionHeader title="All roles" />
          <ul className="divide-y divide-border border-y border-border">
            {roles.map((role) => (
              <li key={role.id} className="space-y-1 py-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
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
                  {role.permission_codes.length} permission
                  {role.permission_codes.length === 1 ? "" : "s"}
                  {role.system_key ? ` · ${role.system_key}` : ""}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </DashboardShell>
  );
}
