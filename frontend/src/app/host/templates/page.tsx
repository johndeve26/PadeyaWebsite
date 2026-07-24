"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
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
  StatusBadge,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  archiveEventTemplate,
  createEventTemplate,
  fetchEventTemplates,
  restoreEventTemplate,
} from "@/lib/templates-api";
import type { EventTemplate } from "@/lib/types/lifecycle";

function parsePayloadJson(raw: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed) return {};
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return null;
    }
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}

export default function HostTemplatesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<EventTemplate[]>([]);
  const [search, setSearch] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [payloadJson, setPayloadJson] = useState("{}");
  const [payloadError, setPayloadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load(include = includeArchived) {
    setRows(await fetchEventTemplates(include));
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchEventTemplates(includeArchived);
        if (active) setRows(items);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load templates");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [includeArchived]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) => {
      const haystack = [row.name, row.description, row.status]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [rows, search]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPayloadError(null);
    const payload = parsePayloadJson(payloadJson);
    if (payload === null) {
      setPayloadError("Enter valid JSON object for payload.");
      return;
    }
    try {
      await createEventTemplate({
        name: name.trim(),
        description: description.trim() || null,
        payload,
      });
      setName("");
      setDescription("");
      setPayloadJson("{}");
      toast.push({ title: "Template created", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Create failed";
      setError(detail);
      toast.push({ title: "Could not create template", description: detail, tone: "danger" });
    }
  }

  async function onArchive(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await archiveEventTemplate(id);
      toast.push({ title: "Template archived", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Archive failed";
      setError(detail);
      toast.push({ title: "Archive failed", description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  async function onRestore(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await restoreEventTemplate(id);
      toast.push({ title: "Template restored", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Restore failed";
      setError(detail);
      toast.push({ title: "Restore failed", description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  function renderActions(row: EventTemplate) {
    const busy = busyId === row.id;
    const archived = row.archived_at != null;
    return (
      <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
        <Link href={`/host/templates/${row.id}`}>
          <Button size="sm" variant="secondary">
            View
          </Button>
        </Link>
        {archived ? (
          <ConfirmAction
            label="Restore"
            title="Restore template?"
            description={`Restore “${row.name}” for reuse when creating events.`}
            confirmLabel="Restore template"
            disabled={busy}
            busy={busy}
            onConfirm={() => onRestore(row.id)}
          />
        ) : (
          <ConfirmAction
            label="Archive"
            title="Archive template?"
            description={`Archive “${row.name}”. It will be hidden from active lists until restored.`}
            confirmLabel="Archive template"
            tone="danger"
            disabled={busy}
            busy={busy}
            onConfirm={() => onArchive(row.id)}
          />
        )}
      </div>
    );
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Events"
        title="Event templates"
        description="Reusable event blueprints with JSON payload defaults for faster publishing."
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <Card className="mb-8 max-w-2xl space-y-4">
          <SectionHeader
            title="Create template"
            description="Store default event fields as JSON. Must be a valid object."
          />
          <form className="space-y-4" onSubmit={onCreate}>
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              label="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Textarea
              label="Payload (JSON)"
              value={payloadJson}
              onChange={(e) => {
                setPayloadJson(e.target.value);
                if (payloadError) setPayloadError(null);
              }}
              error={payloadError ?? undefined}
              hint='Example: {"title":"My event","city":"Lagos"}'
              className="min-h-[120px] font-mono text-sm"
              required
            />
            <Button type="submit">Create template</Button>
          </form>
        </Card>

        <div className="space-y-4">
          <SectionHeader
            title="Your templates"
            description={`${filtered.length} template${filtered.length === 1 ? "" : "s"}${includeArchived ? " (including archived)" : ""}.`}
          />

          {!loading && rows.length > 0 ? (
            <FilterBar
              trailing={
                <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[var(--brand-green)]"
                    checked={includeArchived}
                    onChange={(e) => setIncludeArchived(e.target.checked)}
                  />
                  <span className="font-semibold">Show archived</span>
                </label>
              }
            >
              <Input
                label="Search"
                placeholder="Name, description…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </FilterBar>
          ) : null}

          {loading ? null : rows.length === 0 ? (
            <EmptyState
              title="No templates yet"
              description="Save a reusable event blueprint to speed up publishing."
            />
          ) : (
            <DataTable
              rows={filtered}
              rowKey={(row) => row.id}
              emptyTitle="No matching templates"
              emptyDescription="Try a different search term."
              columns={[
                {
                  key: "name",
                  header: "Template",
                  primary: true,
                  cell: (row) => (
                    <div className="space-y-0.5">
                      <p className="font-semibold text-foreground">{row.name}</p>
                      {row.description ? (
                        <p className="line-clamp-2 text-sm text-muted-foreground">{row.description}</p>
                      ) : null}
                    </div>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (row) => (
                    <div className="flex flex-wrap gap-1.5">
                      <StatusBadge status={row.status} />
                      {row.archived_at ? <StatusBadge status="archived" /> : null}
                    </div>
                  ),
                },
                {
                  key: "updated",
                  header: "Updated",
                  cell: (row) => (
                    <span className="text-sm text-muted-foreground">
                      {formatDateTime(row.updated_at)}
                    </span>
                  ),
                },
                {
                  key: "actions",
                  header: "Actions",
                  cell: (row) => renderActions(row),
                },
              ]}
              mobileCard={(row) => (
                <Card className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-foreground">{row.name}</h3>
                    <StatusBadge status={row.status} />
                    {row.archived_at ? <StatusBadge status="archived" /> : null}
                  </div>
                  {row.description ? (
                    <p className="text-sm text-muted-foreground">{row.description}</p>
                  ) : null}
                  <p className="text-xs text-muted-foreground">
                    Updated {formatDateTime(row.updated_at)}
                  </p>
                  {renderActions(row)}
                </Card>
              )}
            />
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
