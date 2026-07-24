"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Input, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createAdminBlogCategory,
  fetchAdminBlogCategories,
  type BlogCategory,
} from "@/lib/blog-api";

export default function AdminBlogCategoriesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<BlogCategory[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await fetchAdminBlogCategories());
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
      await createAdminBlogCategory({
        name,
        slug: slug || undefined,
        description: description || undefined,
      });
      setName("");
      setSlug("");
      setDescription("");
      toast.push({ tone: "success", title: "Category created" });
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
      title="Categories"
      description="Organize posts by topic."
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
        <Input
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Button disabled={busy || !name.trim()} onClick={() => void create()}>
          Add category
        </Button>
      </div>
      <ul className="mt-8 divide-y divide-border rounded-[var(--radius-md)] border border-border">
        {rows.map((c) => (
          <li key={c.id} className="flex justify-between gap-3 px-4 py-3">
            <div>
              <p className="font-semibold text-heading">{c.name}</p>
              <p className="text-xs text-muted-foreground">/{c.slug}</p>
            </div>
            <Link
              href={`/blog/category/${c.slug}`}
              className="text-sm font-semibold text-primary"
              target="_blank"
            >
              View
            </Link>
          </li>
        ))}
        {!rows.length ? (
          <li className="px-4 py-8 text-sm text-muted-foreground">
            No categories yet.
          </li>
        ) : null}
      </ul>
    </DashboardShell>
  );
}
