"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminNotificationsNav } from "@/components/admin/AdminNotificationsNav";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  SkeletonLoader,
  Textarea,
  useToast,
} from "@/components/ui";
import {
  createAdminNotificationTemplate,
  fetchAdminNotificationTemplates,
  type AdminNotificationTemplate,
} from "@/lib/admin-notifications/api";
import { ApiError } from "@/lib/api";

export default function AdminNotificationTemplatesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<AdminNotificationTemplate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await fetchAdminNotificationTemplates());
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void load();
    });
    return () => {
      cancelled = true;
    };
  }, [load]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createAdminNotificationTemplate({
        name,
        title_template: title,
        body_template: body,
        cta_url_template: "/dashboard/notifications",
      });
      setName("");
      setTitle("");
      setBody("");
      toast.push({ tone: "success", title: "Template created" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin · Notifications"
        title="Templates"
        description="System and custom templates. Use {{host_name}}, {{event_title}}, {{item_title}} placeholders."
      >
        <AdminNotificationsNav />
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        <Card className="mb-6 space-y-3 p-5">
          <h3 className="font-bold text-foreground">New template</h3>
          <form className="space-y-3" onSubmit={onCreate}>
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Input
              label="Title template"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
            <Textarea
              label="Body template"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              rows={3}
            />
            <Button type="submit" disabled={busy}>
              Create
            </Button>
          </form>
        </Card>

        {!rows ? (
          <SkeletonLoader lines={4} />
        ) : (
          <div className="space-y-3">
            {rows.map((t) => (
              <Card key={t.id} className="space-y-1 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-bold text-foreground">{t.name}</h3>
                  {t.is_system ? (
                    <Badge tone="neutral" size="sm">
                      System
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm text-foreground">{t.title_template}</p>
                <p className="text-sm text-muted-foreground">{t.body_template}</p>
                {t.type_key ? (
                  <p className="font-mono text-xs text-muted-foreground">
                    {t.type_key}
                  </p>
                ) : null}
              </Card>
            ))}
          </div>
        )}
      </DashboardShell>
    </RequireAuth>
  );
}
