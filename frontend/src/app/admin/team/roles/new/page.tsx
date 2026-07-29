"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AdminRolePermissionPicker } from "@/components/admin/AdminRolePermissionPicker";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Input,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  createAdminTeamRole,
  fetchAdminTeamRoles,
  type AdminPermissionGroup,
} from "@/lib/admin-team/api";
import { ApiError } from "@/lib/api";

export default function AdminTeamNewRolePage() {
  const router = useRouter();
  const toast = useToast();
  const [catalog, setCatalog] = useState<AdminPermissionGroup[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      void (async () => {
        try {
          const data = await fetchAdminTeamRoles();
          if (!cancelled) setCatalog(data.permission_catalog);
        } catch (err) {
          if (!cancelled) {
            setError(
              err instanceof ApiError
                ? err.message
                : "Failed to load permissions",
            );
          }
        } finally {
          if (!cancelled) setLoading(false);
        }
      })();
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const role = await createAdminTeamRole({
        name: name.trim(),
        description: description.trim() || undefined,
        permission_codes: Array.from(selected),
      });
      toast.push({
        title: "Role created",
        description: role.name,
        tone: "success",
      });
      router.push(`/admin/team/roles/${role.id}`);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Could not create role";
      setError(message);
      toast.push({ title: "Create failed", description: message, tone: "danger" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Team"
      title="New custom role"
      description="Name the role, then tick the individual features this team should have."
      actions={
        <Link href="/admin/team/roles">
          <Button variant="secondary" size="sm">
            Back
          </Button>
        </Link>
      }
    >
      {loading ? (
        <SkeletonLoader lines={8} />
      ) : (
        <form onSubmit={onSubmit} className="mx-auto max-w-3xl space-y-8">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Role name"
              required
              value={name}
              onChange={(ev) => setName(ev.target.value)}
              placeholder="Event Support"
            />
            <Input
              label="Description"
              value={description}
              onChange={(ev) => setDescription(ev.target.value)}
              placeholder="Respond to tickets; no finance"
            />
          </div>

          <AdminRolePermissionPicker
            catalog={catalog}
            selected={selected}
            onChange={setSelected}
          />

          <Button type="submit" disabled={submitting || name.trim().length < 2}>
            {submitting ? "Creating…" : "Create role"}
          </Button>
        </form>
      )}
    </DashboardShell>
  );
}
