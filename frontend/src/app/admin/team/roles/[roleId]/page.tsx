"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { AdminRolePermissionPicker } from "@/components/admin/AdminRolePermissionPicker";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  Input,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  archiveAdminTeamRole,
  createAdminTeamRole,
  fetchAdminTeamRoles,
  updateAdminTeamRole,
  type AdminPermissionGroup,
  type AdminTeamRole,
} from "@/lib/admin-team/api";
import { ApiError } from "@/lib/api";

export default function AdminTeamRoleDetailPage() {
  const params = useParams();
  const roleId = String(params.roleId || "");
  const router = useRouter();
  const toast = useToast();

  const [role, setRole] = useState<AdminTeamRole | null>(null);
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
          if (cancelled) return;
          setCatalog(data.permission_catalog);
          const found = data.roles.find((r) => r.id === roleId) || null;
          if (!found) {
            setError("Role not found");
            setRole(null);
            return;
          }
          setRole(found);
          setName(found.name);
          setDescription(found.description || "");
          setSelected(new Set(found.permission_codes));
        } catch (err) {
          if (!cancelled) {
            setError(
              err instanceof ApiError ? err.message : "Failed to load role",
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
  }, [roleId]);

  const readOnly = Boolean(role?.is_system);
  const dirty = useMemo(() => {
    if (!role || readOnly) return false;
    const sameName = name.trim() === role.name;
    const sameDesc = (description.trim() || "") === (role.description || "");
    const current = Array.from(selected).sort().join("|");
    const original = [...role.permission_codes].sort().join("|");
    return !(sameName && sameDesc && current === original);
  }, [role, readOnly, name, description, selected]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!role || readOnly) return;
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateAdminTeamRole(role.id, {
        name: name.trim(),
        description: description.trim() || "",
        permission_codes: Array.from(selected),
      });
      setRole(updated);
      setName(updated.name);
      setDescription(updated.description || "");
      setSelected(new Set(updated.permission_codes));
      toast.push({ title: "Role updated", tone: "success" });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Could not update role";
      setError(message);
      toast.push({ title: "Update failed", description: message, tone: "danger" });
    } finally {
      setSubmitting(false);
    }
  }

  async function onDuplicate() {
    if (!role) return;
    setSubmitting(true);
    try {
      const copy = await createAdminTeamRole({
        name: `${role.name} (custom)`,
        description:
          role.description ||
          `Custom copy of ${role.system_key || role.name}`,
        permission_codes: role.permission_codes,
      });
      toast.push({
        title: "Custom role created",
        description: "Edit features freely on the new role.",
        tone: "success",
      });
      router.push(`/admin/team/roles/${copy.id}`);
    } catch (err) {
      toast.push({
        title: "Could not duplicate",
        description: err instanceof ApiError ? err.message : "Error",
        tone: "danger",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function onArchive() {
    if (!role || role.is_system) return;
    setSubmitting(true);
    try {
      await archiveAdminTeamRole(role.id);
      toast.push({ title: "Role archived", tone: "success" });
      router.push("/admin/team/roles");
    } catch (err) {
      toast.push({
        title: "Archive failed",
        description: err instanceof ApiError ? err.message : "Error",
        tone: "danger",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Team"
      title={role?.name || "Role"}
      description={
        readOnly
          ? "System roles are fixed presets. Duplicate as a custom role to tick individual features."
          : "Tick or untick individual features for this custom role."
      }
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
        <form
          onSubmit={(e) => void onSubmit(e)}
          className="mx-auto max-w-3xl space-y-8"
        >
          {error ? <Alert tone="danger">{error}</Alert> : null}
          {readOnly ? (
            <Alert tone="info" title="System role">
              You cannot edit system role features directly. Use{" "}
              <strong>Duplicate as custom</strong> to create an editable copy
              with the same starting permissions.
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Role name"
              required
              value={name}
              disabled={readOnly || submitting}
              onChange={(ev) => setName(ev.target.value)}
            />
            <Input
              label="Description"
              value={description}
              disabled={readOnly || submitting}
              onChange={(ev) => setDescription(ev.target.value)}
            />
          </div>

          <AdminRolePermissionPicker
            catalog={catalog}
            selected={selected}
            onChange={setSelected}
            readOnly={readOnly}
          />

          <div className="flex flex-wrap gap-2">
            {!readOnly ? (
              <Button
                type="submit"
                disabled={submitting || !dirty || name.trim().length < 2}
              >
                {submitting ? "Saving…" : "Save features"}
              </Button>
            ) : null}
            <Button
              type="button"
              variant="secondary"
              disabled={submitting}
              onClick={() => void onDuplicate()}
            >
              Duplicate as custom
            </Button>
            {!readOnly ? (
              <ConfirmAction
                label="Archive"
                title="Archive this role?"
                description="Archived roles cannot be assigned to new team members. Existing members keep access until you change their role."
                confirmLabel="Archive"
                tone="danger"
                disabled={submitting}
                onConfirm={() => onArchive()}
              />
            ) : null}
          </div>
        </form>
      )}
    </DashboardShell>
  );
}
