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
  Media,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  archiveBrowseTile,
  createBrowseTile,
  fetchAdminBrowseTiles,
  publishBrowseTile,
  restoreBrowseTile,
  seedDefaultBrowseTiles,
  updateBrowseTile,
} from "@/lib/cms-api";
import type { CmsBrowseTile } from "@/lib/types/lifecycle";

type FormState = {
  rail: string;
  label: string;
  hint: string;
  href: string;
  image_url: string;
  sort_order: string;
};

const emptyForm: FormState = {
  rail: "interest",
  label: "",
  hint: "",
  href: "",
  image_url: "/brand/browse/nightlife.svg",
  sort_order: "0",
};

const RAILS = [
  { value: "interest", label: "Interest" },
  { value: "city", label: "City" },
  { value: "price", label: "Price range" },
  { value: "when", label: "When & format" },
] as const;

export default function AdminBrowseTilesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<CmsBrowseTile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(true);
  const [createForm, setCreateForm] = useState<FormState>(emptyForm);
  const [createBusy, setCreateBusy] = useState(false);
  const [seedBusy, setSeedBusy] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<FormState>(emptyForm);
  const [editBusy, setEditBusy] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchAdminBrowseTiles(includeArchived);
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
          setError(
            err instanceof ApiError ? err.detail : "Failed to load browse tiles",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  function selectRow(tile: CmsBrowseTile) {
    setSelectedId(tile.id);
    setEditForm({
      rail: tile.rail,
      label: tile.label,
      hint: tile.hint ?? "",
      href: tile.href,
      image_url: tile.image_url,
      sort_order: String(tile.sort_order),
    });
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (
      !createForm.label.trim() ||
      !createForm.href.trim() ||
      !createForm.image_url.trim()
    ) {
      return;
    }
    setCreateBusy(true);
    try {
      await createBrowseTile({
        rail: createForm.rail,
        label: createForm.label.trim(),
        hint: createForm.hint.trim() || undefined,
        href: createForm.href.trim(),
        image_url: createForm.image_url.trim(),
        sort_order: Number(createForm.sort_order) || 0,
      });
      setCreateForm(emptyForm);
      toast.push({ tone: "success", title: "Browse tile created" });
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
    if (
      !selectedId ||
      !editForm.label.trim() ||
      !editForm.href.trim() ||
      !editForm.image_url.trim()
    ) {
      return;
    }
    setEditBusy(true);
    try {
      await updateBrowseTile(selectedId, {
        rail: editForm.rail,
        label: editForm.label.trim(),
        hint: editForm.hint.trim() || "",
        href: editForm.href.trim(),
        image_url: editForm.image_url.trim(),
        sort_order: Number(editForm.sort_order) || 0,
      });
      toast.push({ tone: "success", title: "Browse tile updated" });
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

  async function onSeedDefaults() {
    setSeedBusy(true);
    try {
      const result = await seedDefaultBrowseTiles();
      toast.push({
        tone: "success",
        title:
          result.created > 0
            ? `Seeded ${result.created} default tiles`
            : "Defaults already present",
      });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Seed failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setSeedBusy(false);
    }
  }

  async function runLifecycle(
    id: string,
    action: "publish" | "archive" | "restore",
  ) {
    setBusyId(id);
    try {
      if (action === "publish") await publishBrowseTile(id);
      else if (action === "archive") await archiveBrowseTile(id);
      else await restoreBrowseTile(id);
      toast.push({
        tone: "success",
        title:
          action === "publish"
            ? "Tile published"
            : action === "archive"
              ? "Tile archived"
              : "Tile restored",
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

  function lifecycleActions(tile: CmsBrowseTile) {
    const busy = busyId === tile.id;
    if (tile.status === "draft") {
      return (
        <ConfirmAction
          label="Publish"
          title="Publish this tile?"
          description="It will appear on the homepage browse section."
          confirmLabel="Publish"
          busy={busy}
          onConfirm={() => runLifecycle(tile.id, "publish")}
        />
      );
    }
    if (tile.status === "published") {
      return (
        <ConfirmAction
          label="Archive"
          title="Archive this tile?"
          description="Removes it from the homepage browse section."
          confirmLabel="Archive"
          tone="danger"
          busy={busy}
          onConfirm={() => runLifecycle(tile.id, "archive")}
        />
      );
    }
    if (tile.status === "archived") {
      return (
        <ConfirmAction
          label="Restore"
          title="Restore this tile?"
          description="Returns to draft for editing."
          confirmLabel="Restore"
          busy={busy}
          onConfirm={() => runLifecycle(tile.id, "restore")}
        />
      );
    }
    return null;
  }

  const selected = rows?.find((t) => t.id === selectedId) ?? null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="CMS"
      title="Browse tiles"
      description="Homepage interest, city, price, and when tiles — edit image URLs, labels, and links."
      actions={
        <Button
          variant="secondary"
          disabled={seedBusy || (rows != null && rows.length > 0)}
          onClick={() => void onSeedDefaults()}
        >
          {seedBusy ? "Seeding…" : "Seed defaults"}
        </Button>
      }
    >
      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {rows ? (
        <div className="space-y-8">
          <Card className="space-y-4">
            <SectionHeader eyebrow="New" title="Create browse tile" />
            <form
              onSubmit={(e) => void onCreate(e)}
              className="grid gap-4 sm:grid-cols-2"
            >
              <Select
                label="Rail"
                value={createForm.rail}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, rail: e.target.value }))
                }
              >
                {RAILS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
              <Input
                label="Sort order"
                type="number"
                value={createForm.sort_order}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, sort_order: e.target.value }))
                }
              />
              <Input
                label="Label"
                value={createForm.label}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, label: e.target.value }))
                }
                required
              />
              <Input
                label="Hint"
                value={createForm.hint}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, hint: e.target.value }))
                }
              />
              <div className="sm:col-span-2">
                <Input
                  label="Link href"
                  value={createForm.href}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, href: e.target.value }))
                  }
                  required
                />
              </div>
              <div className="sm:col-span-2">
                <Input
                  label="Image URL"
                  value={createForm.image_url}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, image_url: e.target.value }))
                  }
                  hint="Paste /brand/browse/…, /media/…, or a public CDN URL"
                  required
                />
              </div>
              {createForm.image_url.trim() ? (
                <div className="sm:col-span-2 overflow-hidden rounded-[var(--radius-md)] border border-border">
                  <div className="relative aspect-[16/10] max-w-md bg-ink">
                    <Media
                      src={createForm.image_url.trim()}
                      alt=""
                      className="absolute inset-0 h-full w-full object-cover"
                    />
                  </div>
                </div>
              ) : null}
              <div className="sm:col-span-2">
                <Button
                  type="submit"
                  disabled={
                    createBusy ||
                    !createForm.label.trim() ||
                    !createForm.href.trim() ||
                    !createForm.image_url.trim()
                  }
                >
                  {createBusy ? "Creating…" : "Create tile"}
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
            <EmptyState
              title="No browse tiles yet"
              description="Seed the default set, or create tiles manually above."
            />
          ) : (
            <DataTable
              rows={rows}
              rowKey={(t) => t.id}
              emptyTitle="No browse tiles"
              columns={[
                {
                  key: "preview",
                  header: "Image",
                  cell: (t) => (
                    <div className="relative h-12 w-20 overflow-hidden rounded-[var(--radius-sm)] bg-ink">
                      <Media
                        src={t.image_url}
                        alt=""
                        className="absolute inset-0 h-full w-full object-cover"
                      />
                    </div>
                  ),
                },
                {
                  key: "label",
                  header: "Label",
                  primary: true,
                  cell: (t) => (
                    <button
                      type="button"
                      className="text-left font-semibold text-foreground underline-offset-2 hover:underline"
                      onClick={() => selectRow(t)}
                    >
                      {t.label}
                    </button>
                  ),
                },
                {
                  key: "rail",
                  header: "Rail",
                  cell: (t) => t.rail,
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (t) => <StatusBadge status={t.status} />,
                },
                {
                  key: "order",
                  header: "Order",
                  cell: (t) => t.sort_order,
                },
                {
                  key: "actions",
                  header: "",
                  cell: (t) => (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => selectRow(t)}
                      >
                        Edit
                      </Button>
                      {lifecycleActions(t)}
                    </div>
                  ),
                },
              ]}
            />
          )}

          {selected ? (
            <Card className="space-y-4 border-accent/30">
              <SectionHeader eyebrow="Edit" title={selected.label} />
              <div className="grid gap-4 sm:grid-cols-2">
                <Select
                  label="Rail"
                  value={editForm.rail}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, rail: e.target.value }))
                  }
                >
                  {RAILS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </Select>
                <Input
                  label="Sort order"
                  type="number"
                  value={editForm.sort_order}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, sort_order: e.target.value }))
                  }
                />
                <Input
                  label="Label"
                  value={editForm.label}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, label: e.target.value }))
                  }
                />
                <Input
                  label="Hint"
                  value={editForm.hint}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, hint: e.target.value }))
                  }
                />
                <div className="sm:col-span-2">
                  <Input
                    label="Link href"
                    value={editForm.href}
                    onChange={(e) =>
                      setEditForm((f) => ({ ...f, href: e.target.value }))
                    }
                  />
                </div>
                <div className="sm:col-span-2">
                  <Input
                    label="Image URL"
                    value={editForm.image_url}
                    onChange={(e) =>
                      setEditForm((f) => ({ ...f, image_url: e.target.value }))
                    }
                    hint="Paste /brand/browse/…, /media/…, or a public CDN URL"
                  />
                </div>
                {editForm.image_url.trim() ? (
                  <div className="sm:col-span-2 overflow-hidden rounded-[var(--radius-md)] border border-border">
                    <div className="relative aspect-[16/10] max-w-md bg-ink">
                      <Media
                        src={editForm.image_url.trim()}
                        alt=""
                        className="absolute inset-0 h-full w-full object-cover"
                      />
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={
                    editBusy ||
                    !editForm.label.trim() ||
                    !editForm.href.trim() ||
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
