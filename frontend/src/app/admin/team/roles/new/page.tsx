"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

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

  const selectedCount = useMemo(() => selected.size, [selected]);

  function toggle(code: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

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
      router.push("/admin/team/roles");
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
      description="Name the role and select permissions with checkboxes."
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

          <div className="space-y-6">
            <p className="text-sm text-muted-foreground">
              {selectedCount} permission{selectedCount === 1 ? "" : "s"} selected
            </p>
            {catalog.map((group) => (
              <fieldset key={group.group} className="space-y-3">
                <legend className="font-semibold text-heading">{group.group}</legend>
                <ul className="space-y-2">
                  {group.permissions.map((perm) => (
                    <li key={perm.code}>
                      <label className="flex cursor-pointer items-start gap-3 text-sm">
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={selected.has(perm.code)}
                          onChange={() => toggle(perm.code)}
                        />
                        <span>
                          <span className="font-medium text-heading">
                            {perm.code}
                          </span>
                          {perm.high_level ? (
                            <span className="ml-2 text-xs text-muted-foreground">
                              (super admin only)
                            </span>
                          ) : null}
                          <span className="block text-muted-foreground">
                            {perm.description}
                          </span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </fieldset>
            ))}
          </div>

          <Button type="submit" disabled={submitting || name.trim().length < 2}>
            {submitting ? "Creating…" : "Create role"}
          </Button>
        </form>
      )}
    </DashboardShell>
  );
}
