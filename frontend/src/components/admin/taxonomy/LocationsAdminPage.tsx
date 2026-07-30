"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { TaxonomyManager } from "@/components/admin/taxonomy/TaxonomyManager";
import {
  TaxonomyVisualsEditor,
  type TaxonomyVisualFields,
  IMAGE_CAPABLE_LOCATION_KINDS,
} from "@/components/admin/taxonomy/TaxonomyVisualsEditor";
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
import { ApiError, apiRequest } from "@/lib/api";

type LocationRow = {
  id: string;
  kind: string;
  name: string;
  slug: string;
  parent_id?: string | null;
  state_code?: string | null;
  country_code?: string | null;
  is_active?: boolean;
  primary_image_url?: string | null;
  primary_image_alt?: string | null;
  primary_image_focal_x?: number | null;
  primary_image_focal_y?: number | null;
  hero_image_url?: string | null;
  hero_image_alt?: string | null;
  hero_image_focal_x?: number | null;
  hero_image_focal_y?: number | null;
};

const KINDS = ["country", "state", "city", "area"] as const;

export function LocationsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<LocationRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<string>("city");
  const [parentId, setParentId] = useState("");
  const [slug, setSlug] = useState("");
  const [visualsFor, setVisualsFor] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await apiRequest<LocationRow[]>(
          "/taxonomy/admin/locations?include_inactive=true",
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
      const data = await apiRequest<LocationRow[]>(
        "/taxonomy/admin/locations?include_inactive=true",
      );
      setRows(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load");
      setRows([]);
    }
  }

  const parentOptions = useMemo(() => {
    if (!rows) return [];
    return rows.filter((r) => r.is_active !== false && r.kind !== "area");
  }, [rows]);

  const treeRows = useMemo(() => {
    if (!rows) return [];
    const byParent = new Map<string | null, LocationRow[]>();
    for (const row of rows) {
      const key = row.parent_id ?? null;
      const list = byParent.get(key) ?? [];
      list.push(row);
      byParent.set(key, list);
    }
    for (const list of byParent.values()) {
      list.sort((a, b) => {
        const kindCmp = a.kind.localeCompare(b.kind);
        if (kindCmp !== 0) return kindCmp;
        return a.name.localeCompare(b.name);
      });
    }
    const out: { row: LocationRow; depth: number }[] = [];
    function walk(parent: string | null, depth: number) {
      for (const row of byParent.get(parent) ?? []) {
        out.push({ row, depth });
        walk(row.id, depth + 1);
      }
    }
    walk(null, 0);
    // Orphans whose parent is missing from the list
    const seen = new Set(out.map((o) => o.row.id));
    for (const row of rows) {
      if (!seen.has(row.id)) out.push({ row, depth: 0 });
    }
    return out;
  }, [rows]);

  async function onCreate() {
    try {
      await apiRequest("/taxonomy/admin/locations", {
        method: "POST",
        body: {
          name,
          kind,
          slug: slug || undefined,
          parent_id: parentId || null,
        },
      });
      setName("");
      setSlug("");
      setParentId("");
      toast.push({ tone: "success", title: "Location created" });
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
    await apiRequest(`/taxonomy/admin/locations/${id}/archive`, {
      method: "POST",
    });
    toast.push({ tone: "success", title: "Archived" });
    await load();
  }

  async function onRestore(id: string) {
    await apiRequest(`/taxonomy/admin/locations/${id}/restore`, {
      method: "POST",
    });
    toast.push({ tone: "success", title: "Restored" });
    await load();
  }

  return (
    <RequireAuth roles={["super_admin"]}>
      <DashboardShell
        tone="soft"
        eyebrow="Admin · Taxonomy"
        title="Locations"
        description="Hierarchical geography (country → state → city → area). Archive instead of hard-delete."
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
        <TaxonomyManager>
          <Card className="space-y-3">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              New location
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
              <Select
                label="Kind"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
              >
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </Select>
              <Select
                label="Parent"
                value={parentId}
                onChange={(e) => setParentId(e.target.value)}
              >
                <option value="">None (root)</option>
                {parentOptions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.kind}: {p.name}
                  </option>
                ))}
              </Select>
            </div>
            <Button disabled={!name.trim()} onClick={() => void onCreate()}>
              Create
            </Button>
          </Card>

          {rows === null ? (
            <SkeletonLoader lines={6} />
          ) : treeRows.length === 0 ? (
            <EmptyState
              title="No locations yet"
              description="Create locations or run the demo taxonomy seed."
            />
          ) : (
            <div className="space-y-2">
              {treeRows.map(({ row, depth }) => (
                <Card
                  key={row.id}
                  className="flex flex-col gap-3"
                  style={{ marginLeft: depth * 16 }}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-foreground">{row.name}</span>
                    <Badge tone="outline" size="sm">
                      {row.kind}
                    </Badge>
                    <Badge tone="outline" size="sm">
                      {row.slug}
                    </Badge>
                    {row.is_active === false ? (
                      <Badge tone="neutral" size="sm">
                        Archived
                      </Badge>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {row.is_active !== false &&
                    IMAGE_CAPABLE_LOCATION_KINDS.has(row.kind) ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          setVisualsFor((cur) =>
                            cur === row.id ? null : row.id,
                          )
                        }
                      >
                        {visualsFor === row.id ? "Hide visuals" : "Visuals"}
                      </Button>
                    ) : null}
                    {row.is_active !== false ? (
                      <ConfirmAction
                        label="Archive"
                        title={`Archive ${row.name}?`}
                        description="Hidden from public city hubs; not hard-deleted."
                        confirmLabel="Archive"
                        variant="ghost"
                        onConfirm={() => onArchive(row.id)}
                      />
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
                  {row.is_active !== false &&
                  visualsFor === row.id &&
                  IMAGE_CAPABLE_LOCATION_KINDS.has(row.kind) ? (
                    <TaxonomyVisualsEditor
                      kind={row.kind as "city" | "state" | "area"}
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
                </Card>
              ))}
            </div>
          )}
        </TaxonomyManager>
      </DashboardShell>
    </RequireAuth>
  );
}
