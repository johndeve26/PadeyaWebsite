"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createAdminCategory,
  deactivateAdminCategory,
  fetchAdminCategories,
  restoreAdminCategory,
  updateAdminCategory,
} from "@/lib/admin-lifecycle-api";
import type { EventCategory } from "@/lib/types/lifecycle";

type CreateForm = { name: string; slug: string; description: string };

const emptyCreate: CreateForm = { name: "", slug: "", description: "" };

export default function AdminCategoriesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<EventCategory[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeInactive, setIncludeInactive] = useState(true);
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate);
  const [createBusy, setCreateBusy] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editBusy, setEditBusy] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchAdminCategories(includeInactive);
    setRows(data);
  }, [includeInactive]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load categories");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  function selectRow(cat: EventCategory) {
    setSelectedId(cat.id);
    setEditName(cat.name);
    setEditDescription(cat.description ?? "");
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!createForm.name.trim()) return;
    setCreateBusy(true);
    try {
      await createAdminCategory({
        name: createForm.name.trim(),
        slug: createForm.slug.trim() || undefined,
        description: createForm.description.trim() || undefined,
      });
      setCreateForm(emptyCreate);
      toast.push({ tone: "success", title: "Category created" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Create failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setCreateBusy(false);
    }
  }

  async function onSaveEdit() {
    if (!selectedId || !editName.trim()) return;
    setEditBusy(true);
    try {
      await updateAdminCategory(selectedId, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
      });
      toast.push({ tone: "success", title: "Category updated" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Update failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setEditBusy(false);
    }
  }

  async function onDeactivate(id: string) {
    setBusyId(id);
    try {
      await deactivateAdminCategory(id);
      toast.push({ tone: "success", title: "Category deactivated" });
      if (selectedId === id) setSelectedId(null);
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Deactivate failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onRestore(id: string) {
    setBusyId(id);
    try {
      await restoreAdminCategory(id);
      toast.push({ tone: "success", title: "Category restored" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Restore failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  const selected = rows?.find((c) => c.id === selectedId) ?? null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Event categories"
      description="Manage platform-wide event categories. Deactivate instead of delete."
    >
      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {rows ? (
        <div className="space-y-8">
          <Card className="space-y-4">
            <SectionHeader
              eyebrow="New"
              title="Create category"
              description="Slug is optional — generated from the name if omitted."
            />
            <form onSubmit={(e) => void onCreate(e)} className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Name"
                value={createForm.name}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, name: e.target.value }))
                }
                required
              />
              <Input
                label="Slug"
                hint="Optional URL slug"
                value={createForm.slug}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, slug: e.target.value }))
                }
              />
              <div className="sm:col-span-2">
                <Textarea
                  label="Description"
                  value={createForm.description}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, description: e.target.value }))
                  }
                  rows={2}
                />
              </div>
              <div>
                <Button type="submit" disabled={createBusy || !createForm.name.trim()}>
                  {createBusy ? "Creating…" : "Create category"}
                </Button>
              </div>
            </form>
          </Card>

          <FilterBar>
            <label className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border accent-primary"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
              />
              Include inactive
            </label>
          </FilterBar>

          {rows.length === 0 && !error ? (
            <EmptyState
              title="No categories yet"
              description="Create your first event category above."
            />
          ) : (
            <DataTable
              rows={rows}
              rowKey={(c) => c.id}
              emptyTitle="No categories"
              columns={[
                {
                  key: "name",
                  header: "Name",
                  primary: true,
                  cell: (c) => (
                    <button
                      type="button"
                      className="text-left font-semibold text-foreground underline-offset-2 hover:underline"
                      onClick={() => selectRow(c)}
                    >
                      {c.name}
                    </button>
                  ),
                },
                {
                  key: "slug",
                  header: "Slug",
                  cell: (c) => (
                    <span className="font-mono text-sm text-muted-foreground">{c.slug}</span>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (c) => (
                    <StatusBadge
                      status={c.is_active ? "active" : "inactive"}
                      label={c.is_active ? "Active" : "Inactive"}
                    />
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  cell: (c) => (
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="ghost" onClick={() => selectRow(c)}>
                        Edit
                      </Button>
                      {c.is_active ? (
                        <ConfirmAction
                          label="Deactivate"
                          title="Deactivate category?"
                          description="Events keep their category reference; new events won't see this category."
                          confirmLabel="Deactivate"
                          tone="danger"
                          busy={busyId === c.id}
                          onConfirm={() => onDeactivate(c.id)}
                        />
                      ) : (
                        <ConfirmAction
                          label="Restore"
                          title="Restore category?"
                          description="Makes this category available for new events again."
                          confirmLabel="Restore"
                          busy={busyId === c.id}
                          onConfirm={() => onRestore(c.id)}
                        />
                      )}
                    </div>
                  ),
                },
              ]}
            />
          )}

          {selected ? (
            <Card className="space-y-4 border-accent/30">
              <SectionHeader
                eyebrow="Edit"
                title={selected.name}
                description={`Slug: ${selected.slug}`}
              />
              <Input
                label="Name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
              <Textarea
                label="Description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={editBusy || !editName.trim()}
                  onClick={() => void onSaveEdit()}
                >
                  {editBusy ? "Saving…" : "Save changes"}
                </Button>
                <Button variant="ghost" onClick={() => setSelectedId(null)}>
                  Close
                </Button>
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      {rows == null && !error ? <SkeletonLoader lines={4} /> : null}
    </DashboardShell>
  );
}
