"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Input,
  Select,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createMaintenanceNotification,
  fetchMaintenanceNotifications,
  testMaintenanceNotification,
} from "@/lib/maintenance-api";

export default function AdminMaintenanceNotificationsPage() {
  const toast = useToast();
  const [title, setTitle] = useState("Scheduled maintenance on Pàdéyá");
  const [body, setBody] = useState(
    "We will perform scheduled maintenance soon. Some features may be unavailable.",
  );
  const [audience, setAudience] = useState("all_users");
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetchMaintenanceNotifications();
      setItems(res.items);
    } catch {
      /* empty */
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load() hydrates notification list
    void load();
  }, [load]);

  async function send(test: boolean) {
    setBusy(true);
    try {
      const payload = {
        title,
        body,
        audience: test ? "self" : audience,
        channels: ["in_app", "email"],
        send_now: !test,
      };
      if (test) {
        await testMaintenanceNotification(payload);
        toast.push({ tone: "success", title: "Test sent to you" });
      } else {
        await createMaintenanceNotification(payload);
        toast.push({ tone: "success", title: "Notification sent" });
        await load();
      }
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Send failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Platform"
      title="Maintenance notifications"
      description="Notify users before or during maintenance windows."
    >
      <div className="mx-auto max-w-xl space-y-4">
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Textarea
          label="Body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
        />
        <Select
          label="Audience"
          value={audience}
          onChange={(e) => setAudience(e.target.value)}
        >
          <option value="all_users">All users</option>
          <option value="admins">Admins / support</option>
          <option value="hosts">Hosts (approx. all active)</option>
        </Select>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" disabled={busy} onClick={() => void send(false)}>
            Send now
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => void send(true)}
          >
            Test to self
          </Button>
        </div>
        <Alert tone="info" title="Channels">
          In-app + email (security_alert template). Push rides in-app when selected.
        </Alert>
        <ul className="space-y-2 text-sm text-muted-foreground">
          {items.map((n) => (
            <li key={String(n.id)}>
              {String(n.status)} — {String(n.title)} ({String(n.delivery_count || 0)}{" "}
              deliveries)
            </li>
          ))}
        </ul>
      </div>
    </DashboardShell>
  );
}
