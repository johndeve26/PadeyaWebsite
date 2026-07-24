"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  Input,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  adminHideFan,
  adminRestoreFan,
  fetchAdminFans,
} from "@/lib/passport-api";
import type { AdminFanRow } from "@/lib/types/passport";

export default function AdminFansPage() {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [visibility, setVisibility] = useState("any");
  const [refreshKey, setRefreshKey] = useState(0);
  const [rows, setRows] = useState<AdminFanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetchAdminFans({
          q: q.trim() || undefined,
          visibility: visibility === "any" ? undefined : visibility,
          include_hidden: true,
          limit: 60,
        });
        if (!active) return;
        setRows(res.items);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof ApiError ? err.detail : "Failed to load fans");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [q, visibility, refreshKey]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Fan Passports"
      description="Moderate public Fan Passport Directory visibility. Private order and payment data are never shown here."
      actions={
        <Link href="/fans">
          <Button variant="secondary">View public directory</Button>
        </Link>
      }
    >
      <Card className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <Input
            label="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Username, name, or email"
          />
          <Select
            label="Visibility"
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
          >
            <option value="any">Any</option>
            <option value="public">Public</option>
            <option value="unlisted">Unlisted</option>
            <option value="private">Private</option>
          </Select>
          <div className="flex items-end">
            <Button
              type="button"
              onClick={() => {
                setLoading(true);
                setRefreshKey((k) => k + 1);
              }}
            >
              Refresh
            </Button>
          </div>
        </div>
      </Card>

      {error ? (
        <Alert tone="danger" title="Could not load">
          {error}
        </Alert>
      ) : null}

      {loading ? <SkeletonLoader lines={5} /> : null}

      {!loading && rows.length === 0 ? (
        <EmptyState
          title="No Fan Passports match"
          description="Try a different search or visibility filter."
        />
      ) : null}

      <ul className="space-y-3">
        {rows.map((row) => (
          <li key={row.user_id}>
            <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-extrabold text-foreground">
                    {row.display_name}
                  </p>
                  {row.username ? (
                    <Badge tone="outline" size="sm">
                      @{row.username}
                    </Badge>
                  ) : null}
                  <Badge
                    tone={row.visibility === "public" ? "accent" : "neutral"}
                    size="sm"
                  >
                    {row.visibility}
                  </Badge>
                  {row.appear_in_directory ? (
                    <Badge tone="success" size="sm">
                      Directory
                    </Badge>
                  ) : null}
                  {row.admin_hidden ? (
                    <Badge tone="danger" size="sm">
                      Hidden
                    </Badge>
                  ) : null}
                  {!row.user_active ? (
                    <Badge tone="warning" size="sm">
                      Inactive user
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm text-muted-foreground">
                  Events attended (cached): {row.events_attended}
                  {row.admin_hidden_reason
                    ? ` · Hide reason: ${row.admin_hidden_reason}`
                    : ""}
                </p>
                {row.share_path ? (
                  <Link
                    href={row.share_path}
                    className="text-sm font-semibold text-foreground underline-offset-2 hover:underline"
                  >
                    {row.share_path}
                  </Link>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                {row.admin_hidden ? (
                  <ConfirmAction
                    label="Restore"
                    title="Restore Fan Passport?"
                    description="This Passport can be reached again if visibility allows. Directory listing still requires opt-in."
                    confirmLabel="Restore"
                    requireReason
                    reasonLabel="Restore note"
                    onConfirm={async (note) => {
                      await adminRestoreFan(row.user_id, note || "restored");
                      toast.push({ tone: "success", title: "Passport restored" });
                      setLoading(true);
                      setRefreshKey((k) => k + 1);
                    }}
                  />
                ) : (
                  <ConfirmAction
                    label="Hide"
                    title="Hide Fan Passport?"
                    description="Hides from /fans and blocks /f/{username} with a privacy-safe 404."
                    confirmLabel="Hide"
                    tone="danger"
                    requireReason
                    reasonLabel="Hide reason"
                    onConfirm={async (note) => {
                      await adminHideFan(row.user_id, note || "hidden");
                      toast.push({ tone: "success", title: "Passport hidden" });
                      setLoading(true);
                      setRefreshKey((k) => k + 1);
                    }}
                  />
                )}
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </DashboardShell>
  );
}
