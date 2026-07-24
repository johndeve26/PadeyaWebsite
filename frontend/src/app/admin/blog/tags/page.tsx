"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Input, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createAdminBlogTag,
  fetchAdminBlogTags,
  type BlogTag,
} from "@/lib/blog-api";

export default function AdminBlogTagsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<BlogTag[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await fetchAdminBlogTags());
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate list
    void load();
  }, [load]);

  async function create() {
    setBusy(true);
    try {
      await createAdminBlogTag({ name, slug: slug || undefined });
      setName("");
      setSlug("");
      toast.push({ tone: "success", title: "Tag created" });
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Create failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Blog"
      title="Tags"
      description="Cross-cutting labels for discovery."
      actions={
        <Link href="/admin/blog" className="text-sm font-semibold text-primary">
          Back to posts
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      <div className="mx-auto max-w-xl space-y-3">
        <Input
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label="Slug (optional)"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
        />
        <Button disabled={busy || !name.trim()} onClick={() => void create()}>
          Add tag
        </Button>
      </div>
      <ul className="mt-8 divide-y divide-border rounded-[var(--radius-md)] border border-border">
        {rows.map((t) => (
          <li key={t.id} className="flex justify-between gap-3 px-4 py-3">
            <div>
              <p className="font-semibold text-heading">{t.name}</p>
              <p className="text-xs text-muted-foreground">/{t.slug}</p>
            </div>
            <Link
              href={`/blog/tag/${t.slug}`}
              className="text-sm font-semibold text-primary"
              target="_blank"
            >
              View
            </Link>
          </li>
        ))}
        {!rows.length ? (
          <li className="px-4 py-8 text-sm text-muted-foreground">
            No tags yet.
          </li>
        ) : null}
      </ul>
    </DashboardShell>
  );
}
