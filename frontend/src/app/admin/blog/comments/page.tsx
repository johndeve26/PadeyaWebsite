"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Input,
  Select,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminBlogComments,
  updateBlogComment,
  type BlogCommentAdmin,
} from "@/lib/blog-api";

function formatDate(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export default function AdminBlogCommentsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<BlogCommentAdmin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("published");
  const [q, setQ] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [editReason, setEditReason] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(
        await fetchAdminBlogComments({
          status: status || undefined,
          limit: 100,
        }),
      );
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load comments");
    }
  }, [status]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate list
    void load();
  }, [load]);

  const filtered = rows.filter((r) => {
    if (!q.trim()) return true;
    const hay = `${r.display_name} ${r.body}`.toLowerCase();
    return hay.includes(q.trim().toLowerCase());
  });

  function startEdit(row: BlogCommentAdmin) {
    setEditingId(row.id);
    setEditBody(row.body);
    setEditReason("");
  }

  async function saveEdit(id: string) {
    const trimmed = editBody.trim();
    if (trimmed.length < 2) {
      toast.push({
        tone: "danger",
        title: "Comment must be at least 2 characters.",
      });
      return;
    }
    setBusy(true);
    try {
      const updated = await updateBlogComment(id, {
        body: trimmed,
        edit_reason: editReason.trim() || undefined,
      });
      setRows((prev) =>
        prev.map((r) => (r.id === id ? { ...r, ...updated } : r)),
      );
      setEditingId(null);
      toast.push({ tone: "success", title: "Comment updated" });
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Save failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Content"
      title="Blog comments"
      description="Moderate and edit comments across Pàdéyá editorial posts."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link
            href="/admin/blog"
            className="inline-flex h-9 items-center rounded-[var(--radius-sm)] border border-border px-3 text-sm font-semibold"
          >
            Posts
          </Link>
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Refresh
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-[10rem]">
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="published">Published</option>
              <option value="hidden">Hidden</option>
              <option value="archived">Archived</option>
              <option value="">All</option>
            </Select>
          </div>
          <Input
            label="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Name or comment text"
          />
        </div>

        {error ? <Alert tone="danger">{error}</Alert> : null}

        {filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground">No comments found.</p>
        ) : (
          <ul className="space-y-4">
            {filtered.map((row) => (
              <li
                key={row.id}
                className="rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)]"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-heading">
                        {row.display_name}
                      </p>
                      <Badge tone="neutral">{row.status}</Badge>
                      {row.is_edited ? (
                        <Badge tone="accent">
                          {row.edited_by_moderator
                            ? "Moderator edit"
                            : "Edited"}
                        </Badge>
                      ) : null}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(row.created_at)}
                      {row.guest_email ? ` · ${row.guest_email}` : null}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {editingId === row.id ? null : (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy || row.status === "archived"}
                        onClick={() => startEdit(row)}
                      >
                        Edit
                      </Button>
                    )}
                  </div>
                </div>

                {editingId === row.id ? (
                  <div className="mt-4 space-y-3">
                    <Textarea
                      label="Comment body"
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                      rows={4}
                      maxLength={2000}
                    />
                    <Input
                      label="Edit reason (internal)"
                      value={editReason}
                      onChange={(e) => setEditReason(e.target.value)}
                      maxLength={500}
                      hint="Stored in audit history — not shown on the public post"
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={busy}
                        onClick={() => void saveEdit(row.id)}
                      >
                        {busy ? "Saving…" : "Save changes"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => setEditingId(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-foreground/85">
                    {row.body}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </DashboardShell>
  );
}
