"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SectionHeader,
  Select,
  SkeletonLoader,
  Textarea,
  useToast,
} from "@/components/ui";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ApiError, apiRequest } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { useAuth } from "@/components/auth/AuthProvider";
import { formatDateTime } from "@/lib/format";

type AppealRow = {
  id: string;
  user_id: string;
  user_email?: string | null;
  user_full_name?: string | null;
  message: string;
  status: string;
  admin_reply?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  suspension?: {
    reason_category_label: string;
    duration_label: string;
    starts_at: string;
    ends_at: string | null;
  } | null;
};

function AppealsAdminInner() {
  const { user } = useAuth();
  const toast = useToast();
  const canReview = userHasPermission(
    user,
    "admin.appeals.review",
    "admin.users.suspend",
  );
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState<AppealRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AppealRow | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!canReview) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const q = status ? `?status=${encodeURIComponent(status)}` : "";
      const data = await apiRequest<{ items: AppealRow[] }>(
        `/admin/appeals${q}`,
      );
      setItems(data.items || []);
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Could not load appeals",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setLoading(false);
    }
  }, [canReview, status, toast]);

  useEffect(() => {
    // Intentional mount/filter fetch for admin appeals list.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load() updates list state
    void load();
  }, [load]);

  async function decide(kind: "approve" | "reject") {
    if (!selected || busy) return;
    setBusy(true);
    try {
      await apiRequest(`/admin/appeals/${selected.id}/${kind}`, {
        method: "POST",
        body: JSON.stringify({ admin_reply: reply.trim() || null }),
      });
      toast.push({
        tone: "success",
        title: kind === "approve" ? "Appeal approved" : "Appeal rejected",
      });
      setSelected(null);
      setReply("");
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Action failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusy(false);
    }
  }

  if (!canReview) {
    return (
      <Alert tone="warning" title="Permission required">
        You need appeal review or suspend permission to manage appeals.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3">
        <Select
          label="Status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="">All</option>
        </Select>
        <Button type="button" variant="secondary" size="sm" onClick={() => void load()}>
          Refresh
        </Button>
      </div>

      {loading ? (
        <SkeletonLoader lines={6} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No appeals"
          description="Suspension appeals will appear here."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((row) => (
            <li key={row.id}>
              <Card className="space-y-2 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-bold text-foreground">
                      {row.user_full_name || "User"}{" "}
                      <span className="font-normal text-muted-foreground">
                        {row.user_email}
                      </span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(row.created_at)}
                    </p>
                  </div>
                  <Badge>{row.status}</Badge>
                </div>
                <p className="text-sm text-foreground">{row.message}</p>
                {row.suspension ? (
                  <p className="text-xs text-muted-foreground">
                    {row.suspension.reason_category_label} ·{" "}
                    {row.suspension.duration_label} · started{" "}
                    {formatDateTime(row.suspension.starts_at)}
                  </p>
                ) : null}
                {row.status === "pending" ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      setSelected(row);
                      setReply("");
                    }}
                  >
                    Review
                  </Button>
                ) : null}
                <Link
                  href={`/admin/users/${encodeURIComponent(row.user_id)}`}
                  className="text-xs font-medium text-primary underline-offset-2 hover:underline"
                >
                  Open user
                </Link>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {selected ? (
        <Card className="space-y-3 p-4">
          <SectionHeader
            title="Review appeal"
            description={`${selected.user_full_name || "User"} — ${selected.user_email || ""}`}
          />
          <p className="text-sm text-foreground">{selected.message}</p>
          <Textarea
            label="User-facing reply (optional)"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            rows={3}
            placeholder="Shown to the user if you reject (never internal notes)."
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              disabled={busy}
              onClick={() => void decide("approve")}
            >
              Approve & unsuspend
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={() => void decide("reject")}
            >
              Reject
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={busy}
              onClick={() => setSelected(null)}
            >
              Cancel
            </Button>
          </div>
        </Card>
      ) : null}
    </div>
  );
}

export default function AdminAppealsPage() {
  return (
    <RequireAuth roles={["super_admin", "support_agent", "finance_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin"
        title="Appeals"
        description="Review suspension appeals. Approve restores access; reject can include a user-facing reply."
      >
        <AppealsAdminInner />
      </DashboardShell>
    </RequireAuth>
  );
}
