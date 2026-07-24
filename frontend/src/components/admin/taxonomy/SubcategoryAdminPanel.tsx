"use client";

import { useEffect, useState } from "react";

import {
  Badge,
  Button,
  Card,
  ConfirmAction,
  Input,
  useToast,
} from "@/components/ui";
import { ApiError, apiRequest } from "@/lib/api";

type Subcat = {
  id: string;
  name: string;
  slug: string;
  is_active?: boolean;
  archived_at?: string | null;
};

export function SubcategoryAdminPanel({ categoryId }: { categoryId: string }) {
  const toast = useToast();
  const [rows, setRows] = useState<Subcat[] | null>(null);
  const [name, setName] = useState("");
  const [open, setOpen] = useState(false);

  async function load() {
    const data = await apiRequest<Subcat[]>(
      `/taxonomy/admin/categories/${categoryId}/subcategories?include_archived=true`,
    );
    setRows(data);
  }

  useEffect(() => {
    if (!open) return;
    let active = true;
    void (async () => {
      try {
        const data = await apiRequest<Subcat[]>(
          `/taxonomy/admin/categories/${categoryId}/subcategories?include_archived=true`,
        );
        if (!active) return;
        setRows(data);
      } catch {
        if (!active) return;
        setRows([]);
      }
    })();
    return () => {
      active = false;
    };
  }, [categoryId, open]);

  async function onCreate() {
    try {
      await apiRequest(`/taxonomy/admin/categories/${categoryId}/subcategories`, {
        method: "POST",
        body: { name },
      });
      setName("");
      toast.push({ tone: "success", title: "Subcategory created" });
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
    await apiRequest(`/taxonomy/admin/subcategories/${id}/archive`, {
      method: "POST",
    });
    toast.push({ tone: "success", title: "Archived" });
    await load();
  }

  async function onRestore(id: string) {
    await apiRequest(`/taxonomy/admin/subcategories/${id}/restore`, {
      method: "POST",
    });
    toast.push({ tone: "success", title: "Restored" });
    await load();
  }

  return (
    <div className="w-full border-t border-border pt-3">
      <button
        type="button"
        className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground hover:text-foreground"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide subcategories" : "Manage subcategories"}
      </button>
      {open ? (
        <div className="mt-3 space-y-2">
          <div className="flex flex-wrap items-end gap-2">
            <Input
              label="Subcategory name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Button
              size="sm"
              disabled={!name.trim()}
              onClick={() => void onCreate()}
            >
              Add
            </Button>
          </div>
          {rows === null ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No subcategories yet.</p>
          ) : (
            rows.map((row) => (
              <Card
                key={row.id}
                className="flex flex-wrap items-center justify-between gap-2 py-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">
                    {row.name}
                  </span>
                  <Badge tone="outline" size="sm">
                    {row.slug}
                  </Badge>
                  {!row.is_active ? (
                    <Badge tone="neutral" size="sm">
                      Archived
                    </Badge>
                  ) : null}
                </div>
                {row.is_active ? (
                  <ConfirmAction
                    label="Archive"
                    title="Archive subcategory?"
                    description="Hidden from public lists; not hard-deleted."
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
              </Card>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
