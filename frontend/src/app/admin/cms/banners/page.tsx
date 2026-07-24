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
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  archiveBanner,
  createBanner,
  fetchAdminBanners,
  publishBanner,
  restoreBanner,
  updateBanner,
} from "@/lib/cms-api";
import type { CmsBanner } from "@/lib/types/lifecycle";

type CreateForm = {
  title: string;
  subtitle: string;
  image_url: string;
  cta_label: string;
  cta_href: string;
  sort_order: string;
};

const emptyCreate: CreateForm = {
  title: "",
  subtitle: "",
  image_url: "",
  cta_label: "",
  cta_href: "",
  sort_order: "0",
};

export default function AdminBannersPage() {
  const toast = useToast();
  const [rows, setRows] = useState<CmsBanner[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(true);
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate);
  const [createBusy, setCreateBusy] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<CreateForm>(emptyCreate);
  const [editBusy, setEditBusy] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchAdminBanners(includeArchived);
    setRows(data);
  }, [includeArchived]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load banners");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  function selectRow(banner: CmsBanner) {
    setSelectedId(banner.id);
    setEditForm({
      title: banner.title,
      subtitle: banner.subtitle ?? "",
      image_url: banner.image_url,
      cta_label: banner.cta_label ?? "",
      cta_href: banner.cta_href ?? "",
      sort_order: String(banner.sort_order),
    });
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!createForm.title.trim() || !createForm.image_url.trim()) return;
    setCreateBusy(true);
    try {
      await createBanner({
        title: createForm.title.trim(),
        subtitle: createForm.subtitle.trim() || undefined,
        image_url: createForm.image_url.trim(),
        cta_label: createForm.cta_label.trim() || undefined,
        cta_href: createForm.cta_href.trim() || undefined,
        sort_order: Number(createForm.sort_order) || 0,
      });
      setCreateForm(emptyCreate);
      toast.push({ tone: "success", title: "Banner created" });
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
    if (!selectedId || !editForm.title.trim() || !editForm.image_url.trim()) return;
    setEditBusy(true);
    try {
      await updateBanner(selectedId, {
        title: editForm.title.trim(),
        subtitle: editForm.subtitle.trim() || undefined,
        image_url: editForm.image_url.trim(),
        cta_label: editForm.cta_label.trim() || undefined,
        cta_href: editForm.cta_href.trim() || undefined,
        sort_order: Number(editForm.sort_order) || 0,
      });
      toast.push({ tone: "success", title: "Banner updated" });
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

  async function runLifecycle(
    id: string,
    action: "publish" | "archive" | "restore",
  ) {
    setBusyId(id);
    try {
      if (action === "publish") await publishBanner(id);
      else if (action === "archive") await archiveBanner(id);
      else await restoreBanner(id);
      toast.push({
        tone: "success",
        title:
          action === "publish"
            ? "Banner published"
            : action === "archive"
              ? "Banner archived"
              : "Banner restored",
      });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Action failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  function lifecycleActions(banner: CmsBanner) {
    const busy = busyId === banner.id;
    if (banner.status === "draft") {
      return (
        <ConfirmAction
          label="Publish"
          title="Publish this banner?"
          description="It will appear in public banner slots."
          confirmLabel="Publish"
          busy={busy}
          onConfirm={() => runLifecycle(banner.id, "publish")}
        />
      );
    }
    if (banner.status === "published") {
      return (
        <ConfirmAction
          label="Archive"
          title="Archive this banner?"
          description="Removes it from public display."
          confirmLabel="Archive"
          tone="danger"
          busy={busy}
          onConfirm={() => runLifecycle(banner.id, "archive")}
        />
      );
    }
    if (banner.status === "archived") {
      return (
        <ConfirmAction
          label="Restore"
          title="Restore this banner?"
          description="Returns to draft for editing."
          confirmLabel="Restore"
          busy={busy}
          onConfirm={() => runLifecycle(banner.id, "restore")}
        />
      );
    }
    return null;
  }

  const selected = rows?.find((b) => b.id === selectedId) ?? null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="CMS"
      title="Banners"
      description="Homepage and marketing banners with optional CTA links."
    >
      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {rows ? (
        <div className="space-y-8">
          <Card className="space-y-4">
            <SectionHeader eyebrow="New" title="Create banner" />
            <form onSubmit={(e) => void onCreate(e)} className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Title"
                value={createForm.title}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, title: e.target.value }))
                }
                required
              />
              <Input
                label="Subtitle"
                value={createForm.subtitle}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, subtitle: e.target.value }))
                }
              />
              <div className="sm:col-span-2">
                <Input
                  label="Image URL"
                  value={createForm.image_url}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, image_url: e.target.value }))
                  }
                  required
                />
              </div>
              <Input
                label="CTA label"
                value={createForm.cta_label}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, cta_label: e.target.value }))
                }
              />
              <Input
                label="CTA href"
                value={createForm.cta_href}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, cta_href: e.target.value }))
                }
              />
              <Input
                label="Sort order"
                type="number"
                value={createForm.sort_order}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, sort_order: e.target.value }))
                }
              />
              <div className="sm:col-span-2">
                <Button
                  type="submit"
                  disabled={
                    createBusy ||
                    !createForm.title.trim() ||
                    !createForm.image_url.trim()
                  }
                >
                  {createBusy ? "Creating…" : "Create banner"}
                </Button>
              </div>
            </form>
          </Card>

          <FilterBar>
            <label className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border accent-primary"
                checked={includeArchived}
                onChange={(e) => setIncludeArchived(e.target.checked)}
              />
              Include archived
            </label>
          </FilterBar>

          {rows.length === 0 && !error ? (
            <EmptyState title="No banners yet" description="Create your first banner above." />
          ) : (
            <DataTable
              rows={rows}
              rowKey={(b) => b.id}
              emptyTitle="No banners"
              columns={[
                {
                  key: "title",
                  header: "Title",
                  primary: true,
                  cell: (b) => (
                    <button
                      type="button"
                      className="text-left font-semibold text-foreground underline-offset-2 hover:underline"
                      onClick={() => selectRow(b)}
                    >
                      {b.title}
                    </button>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (b) => <StatusBadge status={b.status} />,
                },
                {
                  key: "order",
                  header: "Order",
                  cell: (b) => b.sort_order,
                },
                {
                  key: "actions",
                  header: "",
                  cell: (b) => (
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="ghost" onClick={() => selectRow(b)}>
                        Edit
                      </Button>
                      {lifecycleActions(b)}
                    </div>
                  ),
                },
              ]}
            />
          )}

          {selected ? (
            <Card className="space-y-4 border-accent/30">
              <SectionHeader eyebrow="Edit" title={selected.title} />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Title"
                  value={editForm.title}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, title: e.target.value }))
                  }
                />
                <Input
                  label="Subtitle"
                  value={editForm.subtitle}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, subtitle: e.target.value }))
                  }
                />
                <div className="sm:col-span-2">
                  <Input
                    label="Image URL"
                    value={editForm.image_url}
                    onChange={(e) =>
                      setEditForm((f) => ({ ...f, image_url: e.target.value }))
                    }
                  />
                </div>
                <Input
                  label="CTA label"
                  value={editForm.cta_label}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, cta_label: e.target.value }))
                  }
                />
                <Input
                  label="CTA href"
                  value={editForm.cta_href}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, cta_href: e.target.value }))
                  }
                />
                <Input
                  label="Sort order"
                  type="number"
                  value={editForm.sort_order}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, sort_order: e.target.value }))
                  }
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={
                    editBusy ||
                    !editForm.title.trim() ||
                    !editForm.image_url.trim()
                  }
                  onClick={() => void onSaveEdit()}
                >
                  {editBusy ? "Saving…" : "Save changes"}
                </Button>
                <Button variant="ghost" onClick={() => setSelectedId(null)}>
                  Close
                </Button>
                {lifecycleActions(selected)}
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      {rows == null && !error ? <SkeletonLoader lines={4} /> : null}
    </DashboardShell>
  );
}
