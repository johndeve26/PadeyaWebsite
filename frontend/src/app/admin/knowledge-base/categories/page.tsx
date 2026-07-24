"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Input, Select, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createAdminHelpCategory,
  fetchAdminHelpCategories,
  updateAdminHelpCategory,
  type HelpCategory,
} from "@/lib/knowledge-base/api";

const GROUPS = ["fan", "host", "account", "admin", "general"];

export default function AdminKnowledgeBaseCategoriesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<HelpCategory[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [groupKey, setGroupKey] = useState("general");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await fetchAdminHelpCategories());
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
    if (!name.trim()) return;
    setBusy(true);
    try {
      await createAdminHelpCategory({
        name: name.trim(),
        slug: slug.trim() || undefined,
        group_key: groupKey,
        description: description.trim() || undefined,
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

  async function bumpSort(cat: HelpCategory, delta: number) {
    setBusy(true);
    try {
      await updateAdminHelpCategory(cat.id, {
        sort_order: cat.sort_order + delta,
      });
      await load();
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Update failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Knowledge Base"
      title="Categories"
      description="Organize Help Center topics by audience group."
      actions={
        <Link href="/admin/knowledge-base">
          <Button size="sm" variant="secondary">
            Articles
          </Button>
        </Link>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <section className="mb-10 max-w-xl space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-[0.14em] text-muted-foreground">
          New category
        </h2>
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
        <Select
          label="Group"
          value={groupKey}
          onChange={(e) => setGroupKey(e.target.value)}
        >
          {GROUPS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </Select>
        <Input
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Button disabled={busy || !name.trim()} onClick={() => void create()}>
          Create
        </Button>
      </section>

      <ul className="divide-y divide-border border-t border-border">
        {rows.map((cat) => (
          <li
            key={cat.id}
            className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="font-semibold text-heading">{cat.name}</p>
              <p className="text-xs text-muted-foreground">
                {cat.group_key} · /help/{cat.slug} · {cat.article_count} articles
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => void bumpSort(cat, -10)}
              >
                Up
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => void bumpSort(cat, 10)}
              >
                Down
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </DashboardShell>
  );
}
