"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ImpersonationStartForm } from "@/components/admin/ImpersonationStartForm";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Card, SectionHeader } from "@/components/ui";
import { fetchAdminUser } from "@/lib/admin-lifecycle-api";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import type { AdminUserDetail } from "@/lib/types/lifecycle";

export default function AdminUserImpersonationPage() {
  const params = useParams();
  const userId = String(params.userId ?? "");
  const { user: adminUser } = useAuth();
  const [target, setTarget] = useState<AdminUserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canImpersonate = userHasPermission(adminUser, "admin.users.impersonate");

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const row = await fetchAdminUser(userId);
        if (active) setTarget(row);
      } catch (err) {
        if (active) {
          setTarget(null);
          setError(
            err instanceof ApiError ? err.detail : "Could not load this user",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [userId]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Impersonate user"
      description="Start an audited session to view Pàdéyá as this account for support, QA, or debugging."
    >
      <div className="mb-4">
        <Link
          href={`/admin/users/${encodeURIComponent(userId)}`}
          className="text-sm font-semibold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          ← Back to user
        </Link>
      </div>

      {!canImpersonate ? (
        <Alert tone="danger" title="Permission required">
          You need admin impersonation permission to start a session.
        </Alert>
      ) : loading ? (
        <Card className="max-w-xl p-6 text-sm text-muted-foreground">
          Loading user…
        </Card>
      ) : error ? (
        <Alert tone="danger" title="User not found">
          {error}
        </Alert>
      ) : target ? (
        <Card className="max-w-xl space-y-5">
          <SectionHeader
            eyebrow="Impersonation"
            title={target.full_name}
            description={target.email}
          />
          <ImpersonationStartForm userId={target.id} target={target} />
        </Card>
      ) : null}
    </DashboardShell>
  );
}
