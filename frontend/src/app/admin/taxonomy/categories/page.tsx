"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SubcategoryAdminPanel } from "@/components/admin/taxonomy/SubcategoryAdminPanel";
import {
  TaxonomyVisualsEditor,
  type TaxonomyVisualFields,
} from "@/components/admin/taxonomy/TaxonomyVisualsEditor";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  Input,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";

type TaxTerm = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  sort_order?: number;
  featured?: boolean;
  is_active?: boolean;
  usage_count?: number;
  seo_title?: string | null;
  seo_description?: string | null;
  primary_image_url?: string | null;
  primary_image_alt?: string | null;
  primary_image_focal_x?: number | null;
  primary_image_focal_y?: number | null;
  hero_image_url?: string | null;
  hero_image_alt?: string | null;
  hero_image_focal_x?: number | null;
  hero_image_focal_y?: number | null;
};

function UsageCountBadge({ count }: { count: number }) {
  return (
    <Badge tone={count > 0 ? "warning" : "neutral"} size="sm">
      {count} used
    </Badge>
  );
}

export default function AdminTaxonomyCategoriesPage() {
  const toast = useToast();
  const [rows, setRows] = useState<TaxTerm[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [visualsFor, setVisualsFor] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await apiRequest<TaxTerm[]>(
          "/taxonomy/admin/categories?include_archived=true",
        );
        if (!active) return;
        setRows(data);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err instanceof ApiError ? err.detail : "Failed to load");
        setRows([]);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function load() {
    try {
      const data = await apiRequest<TaxTerm[]>(
        "/taxonomy/admin/categories?include_archived=true",
      );
      setRows(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load");
      setRows([]);
    }
  }

  async function onCreate() {
    try {
      await apiRequest("/taxonomy/admin/categories", {
        method: "POST",
        body: { name, slug: slug || undefined },
      });
      setName("");
      setSlug("");
      toast.push({ tone: "success", title: "Category created" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Create failed",
        description: err instanceof ApiError ? err.detail : "Error",
      });
    }
  }

  async function onArchive(id: string) {
    await apiRequest(`/taxonomy/admin/categories/${id}/archive`, {
      method: "POST",
    });
    toast.push({ tone: "success", title: "Archived" });
    await load();
  }

  async function onRestore(id: string) {
    await apiRequest(`/taxonomy/admin/categories/${id}/restore`, {
      method: "POST",
    });
    toast.push({ tone: "success", title: "Restored" });
    await load();
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin"
        title="Taxonomy · Categories"
        description="Archive instead of delete. Usage counts protect live events."
        actions={
          <Link href="/admin/taxonomy">
            <Button variant="secondary">Taxonomy home</Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}

        <Card className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            New category
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              label="Slug"
              placeholder="auto from name"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
          </div>
          <Button disabled={!name.trim()} onClick={() => void onCreate()}>
            Create
          </Button>
        </Card>

        {rows === null ? (
          <SkeletonLoader lines={6} />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No taxonomy categories yet"
            description="Create categories or run the demo taxonomy seed."
          />
        ) : (
          <div className="space-y-2">
            {rows.map((row) => (
              <Card
                key={row.id}
                className="flex flex-col gap-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-bold text-foreground">{row.name}</p>
                    <Badge tone="outline" size="sm">
                      {row.slug}
                    </Badge>
                    {!row.is_active ? (
                      <Badge tone="neutral" size="sm">
                        Archived
                      </Badge>
                    ) : null}
                    <UsageCountBadge count={row.usage_count ?? 0} />
                  </div>
                  {row.description ? (
                    <p className="text-sm text-muted-foreground">{row.description}</p>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {row.is_active ? (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          setVisualsFor((cur) => (cur === row.id ? null : row.id))
                        }
                      >
                        {visualsFor === row.id ? "Hide visuals" : "Visuals"}
                      </Button>
                      <ConfirmAction
                      label="Archive"
                      title="Archive this category?"
                      description={
                        (row.usage_count ?? 0) > 0
                          ? `Used by ${row.usage_count} events/links. Archive hides it from public hubs; it is not hard-deleted.`
                          : "This category will be hidden from public discovery."
                      }
                      confirmLabel="Archive"
                      variant="ghost"
                      onConfirm={() => onArchive(row.id)}
                    />
                    </>
                  ) : (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void onRestore(row.id)}
                    >
                      Restore
                    </Button>
                  )}
                </div>
                </div>
                {row.is_active && visualsFor === row.id ? (
                  <TaxonomyVisualsEditor
                    kind="category"
                    termId={row.id}
                    termName={row.name}
                    value={{
                      primary_image_url: row.primary_image_url,
                      primary_image_alt: row.primary_image_alt,
                      primary_image_focal_x: row.primary_image_focal_x,
                      primary_image_focal_y: row.primary_image_focal_y,
                      hero_image_url: row.hero_image_url,
                      hero_image_alt: row.hero_image_alt,
                      hero_image_focal_x: row.hero_image_focal_x,
                      hero_image_focal_y: row.hero_image_focal_y,
                    }}
                    onChange={(next: TaxonomyVisualFields) => {
                      setRows((cur) =>
                        (cur ?? []).map((r) =>
                          r.id === row.id ? { ...r, ...next } : r,
                        ),
                      );
                    }}
                  />
                ) : null}
                {row.is_active ? (
                  <SubcategoryAdminPanel categoryId={row.id} />
                ) : null}
              </Card>
            ))}
          </div>
        )}
      </DashboardShell>
    </RequireAuth>
  );
}
