"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  Input,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useUnsavedChanges } from "@/lib/hooks/useUnsavedChanges";
import {
  archiveEventTemplate,
  fetchEventTemplate,
  restoreEventTemplate,
  updateEventTemplate,
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

function payloadToJson(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2);
}

export default function HostTemplateDetailPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [template, setTemplate] = useState<EventTemplate | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [payloadJson, setPayloadJson] = useState("{}");
  const [payloadError, setPayloadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyLifecycle, setBusyLifecycle] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchEventTemplate(params.id);
        if (!active) return;
        setTemplate(row);
        setName(row.name);
        setDescription(row.description ?? "");
        setPayloadJson(payloadToJson(row.payload));
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load template");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  const dirty = useMemo(() => {
    if (!template) return false;
    const payloadDirty = payloadJson !== payloadToJson(template.payload);
    return (
      name !== template.name ||
      description !== (template.description ?? "") ||
      payloadDirty
    );
  }, [template, name, description, payloadJson]);

  useUnsavedChanges(dirty);

  async function reload() {
    const row = await fetchEventTemplate(params.id);
    setTemplate(row);
    setName(row.name);
    setDescription(row.description ?? "");
    setPayloadJson(payloadToJson(row.payload));
    setPayloadError(null);
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!template) return;
    setPayloadError(null);
    const payload = parsePayloadJson(payloadJson);
    if (payload === null) {
      setPayloadError("Enter valid JSON object for payload.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateEventTemplate(template.id, {
        name: name.trim(),
        description: description.trim() || null,
        payload,
      });
      toast.push({ title: "Changes saved", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Save failed";
      setError(detail);
      toast.push({ title: "Save failed", description: detail, tone: "danger" });
    } finally {
      setSaving(false);
    }
  }

  async function onArchive() {
    if (!template) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await archiveEventTemplate(template.id);
      toast.push({ title: "Template archived", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Archive failed";
      setError(detail);
      toast.push({ title: "Archive failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  async function onRestore() {
    if (!template) return;
    setBusyLifecycle(true);
    setError(null);
    try {
      await restoreEventTemplate(template.id);
      toast.push({ title: "Template restored", tone: "success" });
      await reload();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Restore failed";
      setError(detail);
      toast.push({ title: "Restore failed", description: detail, tone: "danger" });
    } finally {
      setBusyLifecycle(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Events"
        title={template?.name ?? "Event template"}
        description="Edit template defaults and lifecycle status."
        actions={
          <Link href="/host/templates">
            <Button variant="ghost">Back to templates</Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {loading && !error ? <SkeletonLoader lines={5} /> : null}

        {!loading && template ? (
          <div className="space-y-6">
            <Card className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={template.status} />
                {template.archived_at ? <StatusBadge status="archived" /> : null}
              </div>
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    Created
                  </dt>
                  <dd className="mt-1 text-muted-foreground">{formatDateTime(template.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    Last updated
                  </dt>
                  <dd className="mt-1 text-muted-foreground">{formatDateTime(template.updated_at)}</dd>
                </div>
              </dl>
            </Card>

            <Card className="max-w-2xl space-y-4">
              <SectionHeader
                title="Edit template"
                description="Payload must remain a valid JSON object."
              />
              <form className="space-y-4" onSubmit={onSave}>
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
                  className="min-h-[200px] font-mono text-sm"
                  required
                />
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" disabled={!dirty || saving}>
                    {saving ? "Saving…" : "Save changes"}
                  </Button>
                  {dirty ? (
                    <span className="self-center text-xs text-muted-foreground">
                      Unsaved changes
                    </span>
                  ) : null}
                </div>
              </form>
            </Card>

            <Card className="max-w-2xl space-y-4">
              <SectionHeader
                title="Lifecycle"
                description={
                  template.archived_at
                    ? "Restore to use this template when creating events."
                    : "Archive to hide from active template lists."
                }
              />
              {template.archived_at ? (
                <ConfirmAction
                  label="Restore template"
                  title="Restore template?"
                  description={`Restore “${template.name}” for reuse when creating events.`}
                  confirmLabel="Restore"
                  disabled={busyLifecycle}
                  busy={busyLifecycle}
                  onConfirm={() => onRestore()}
                />
              ) : (
                <ConfirmAction
                  label="Archive template"
                  title="Archive template?"
                  description={`Archive “${template.name}”. It will be hidden from active lists until restored.`}
                  confirmLabel="Archive"
                  tone="danger"
                  disabled={busyLifecycle}
                  busy={busyLifecycle}
                  onConfirm={() => onArchive()}
                />
              )}
            </Card>
          </div>
        ) : null}

        {!loading && !template && !error ? (
          <Alert tone="warning" title="Not found">
            This template could not be loaded.
          </Alert>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
