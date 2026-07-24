"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Input,
  SkeletonLoader,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminMerchCategories,
  upsertAdminMerchCategory,
  type MerchAdminCategory,
} from "@/lib/merch-api";

export default function AdminMerchCategoriesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<MerchAdminCategory[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    slug: "",
    name: "",
    description: "",
    sort_order: "0",
  });

  const load = useCallback(async () => {
    const data = await fetchAdminMerchCategories();
    setRows(data);
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchAdminMerchCategories();
        if (active) {
          setRows(data);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Failed to load merch categories",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onSave() {
    setSaving(true);
    try {
      await upsertAdminMerchCategory({
        slug: form.slug.trim(),
        name: form.name.trim(),
        description: form.description.trim() || null,
        sort_order: Number(form.sort_order) || 0,
        status: "active",
      });
      toast.push({ tone: "success", title: "Category saved" });
      setForm({ slug: "", name: "", description: "", sort_order: "0" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Could not save category",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Merch categories"
      description="Manage browse categories for the public merch marketplace."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/merchandise">
            <Button variant="secondary" size="sm">
              All merch
            </Button>
          </Link>
          <Link href="/admin/merchandise/reports">
            <Button variant="secondary" size="sm">
              Reports
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load categories">
          {error}
        </Alert>
      ) : null}

      <Card className="space-y-4">
        <h2 className="text-lg font-extrabold text-foreground">
          Add or update category
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block space-y-1.5 text-sm">
            <span className="font-bold">Slug</span>
            <Input
              value={form.slug}
              onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
              placeholder="apparel"
            />
          </label>
          <label className="block space-y-1.5 text-sm">
            <span className="font-bold">Name</span>
            <Input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Apparel"
            />
          </label>
          <label className="block space-y-1.5 text-sm sm:col-span-2">
            <span className="font-bold">Description</span>
            <Textarea
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              rows={2}
            />
          </label>
          <label className="block space-y-1.5 text-sm">
            <span className="font-bold">Sort order</span>
            <Input
              type="number"
              value={form.sort_order}
              onChange={(e) =>
                setForm((f) => ({ ...f, sort_order: e.target.value }))
              }
            />
          </label>
        </div>
        <Button
          size="sm"
          disabled={saving || !form.slug.trim() || !form.name.trim()}
          onClick={() => void onSave()}
        >
          {saving ? "Saving…" : "Save category"}
        </Button>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-extrabold text-foreground">Categories</h2>
        {rows === null ? (
          <SkeletonLoader lines={4} />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No categories yet"
            description="Add a category above to seed the marketplace browse list."
          />
        ) : (
          <ul className="divide-y divide-border">
            {rows.map((row) => (
              <li
                key={row.id || row.slug}
                className="flex flex-wrap items-center justify-between gap-2 py-3"
              >
                <div>
                  <p className="font-extrabold text-foreground">{row.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {row.slug}
                    {row.description ? ` · ${row.description}` : ""}
                  </p>
                </div>
                <p className="text-xs font-bold text-muted-foreground">
                  sort {row.sort_order ?? 0}
                  {row.status ? ` · ${row.status}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </DashboardShell>
  );
}
