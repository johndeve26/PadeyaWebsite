"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Badge, Button, Card, EmptyState, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminEmailTemplates,
  type AdminEmailTemplate,
} from "@/lib/email-api";
import { formatDateTime } from "@/lib/format";

const CATEGORIES = [
  { id: "", label: "All" },
  { id: "account", label: "Account" },
  { id: "tickets", label: "Tickets" },
  { id: "merch", label: "Merch" },
  { id: "hosts_events", label: "Hosts & events" },
  { id: "support_safety", label: "Support & safety" },
  { id: "sponsors_ambassadors", label: "Sponsors & ambassadors" },
  { id: "payments", label: "Payments" },
];

export default function AdminEmailTemplatesPage() {
  const [items, setItems] = useState<AdminEmailTemplate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchAdminEmailTemplates({
          category: category || undefined,
          q: query.trim() || undefined,
        });
        if (active) {
          setItems(rows);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load templates");
          setItems([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [category, query]);

  const sorted = useMemo(
    () => [...items].sort((a, b) => a.title.localeCompare(b.title)),
    [items],
  );

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Platform email templates"
      description="Dedicated admin notifications for Pàdéyá platform events. Edit copy, recipients, and delivery without changing fan or host emails."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/emails">
            <Button size="sm" variant="secondary">
              Outbox
            </Button>
          </Link>
          <Link href="/admin/emails/settings">
            <Button size="sm" variant="secondary">
              Email settings
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="min-w-0 flex-1">
          <Input
            label="Search"
            placeholder="Template key or title"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <Button
              key={c.id || "all"}
              size="sm"
              variant={category === c.id ? "secondary" : "ghost"}
              onClick={() => setCategory(c.id)}
            >
              {c.label}
            </Button>
          ))}
        </div>
      </div>

      {sorted.length === 0 ? (
        <EmptyState title="No templates" description="Adjust filters or run migrations." />
      ) : (
        <ul className="space-y-3">
          {sorted.map((t) => (
            <li key={t.key}>
              <Card padded className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-extrabold text-foreground">{t.title}</p>
                    <Badge tone={t.is_enabled ? "accent" : "outline"} size="sm">
                      {t.is_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                    {t.is_required ? (
                      <Badge tone="outline" size="sm">
                        Required
                      </Badge>
                    ) : null}
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">{t.key}</p>
                  <p className="text-sm text-muted-foreground line-clamp-1">{t.subject}</p>
                  <p className="text-xs text-muted-foreground">
                    {t.category.replace(/_/g, " ")} · {t.recipient_mode.replace(/_/g, " ")} ·{" "}
                    {t.resolved_recipient_count} recipient
                    {t.resolved_recipient_count === 1 ? "" : "s"} · Updated{" "}
                    {formatDateTime(t.updated_at)}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  <Link href={`/admin/emails/templates/${encodeURIComponent(t.key)}`}>
                    <Button size="sm">Edit</Button>
                  </Link>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </DashboardShell>
  );
}
