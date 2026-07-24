"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import {
  TaxonomyManager,
  UsageCountBadge,
} from "@/components/admin/taxonomy/TaxonomyManager";
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

type Term = {
  id: string;
  name: string;
  slug: string;
  is_active?: boolean;
  usage_count?: number;
};

function VocabAdminPage({
  title,
  path,
}: {
  title: string;
  path: string;
}) {
  const toast = useToast();
  const [rows, setRows] = useState<Term[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await apiRequest<Term[]>(
          `/taxonomy/admin/${path}?include_archived=true`,
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
  }, [path]);

  async function load() {
    try {
      const data = await apiRequest<Term[]>(
        `/taxonomy/admin/${path}?include_archived=true`,
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
      await apiRequest(`/taxonomy/admin/${path}`, {
        method: "POST",
        body: { name },
      });
      setName("");
      toast.push({ tone: "success", title: "Created" });
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
    await apiRequest(`/taxonomy/admin/${path}/${id}/archive`, {
      method: "POST",
    });
    toast.push({ tone: "success", title: "Archived" });
    await load();
  }

  async function onRestore(id: string) {
    await apiRequest(`/taxonomy/admin/${path}/${id}/restore`, {
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
        title={title}
        description="Archive instead of hard-delete. See docs/TAXONOMY_AND_CONTENT_GRAPH.md."
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
          <Card className="flex flex-wrap items-end gap-3">
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Button disabled={!name.trim()} onClick={() => void onCreate()}>
              Create
            </Button>
          </Card>
          {rows === null ? (
            <SkeletonLoader lines={4} />
          ) : rows.length === 0 ? (
            <EmptyState title="None yet" description="Create a term or run demo seed." />
          ) : (
            <div className="space-y-2">
              {rows.map((row) => (
                <Card
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-2"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-foreground">{row.name}</span>
                    <Badge tone="outline" size="sm">
                      {row.slug}
                    </Badge>
                    {!row.is_active ? (
                      <Badge tone="neutral" size="sm">
                        Archived
                      </Badge>
                    ) : null}
                    {"usage_count" in row && typeof row.usage_count === "number" ? (
                      <UsageCountBadge count={row.usage_count} />
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {row.is_active ? (
                      <ConfirmAction
                        label="Archive"
                        title={`Archive ${row.name}?`}
                        description="Hidden from public hubs; not hard-deleted."
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
                </Card>
              ))}
            </div>
          )}
        </TaxonomyManager>
      </DashboardShell>
    </RequireAuth>
  );
}

export function TagsPage() {
  return <VocabAdminPage title="Tags" path="tags" />;
}

export function HostTypesPage() {
  return <VocabAdminPage title="Host types" path="host-types" />;
}

export function VenueTypesPage() {
  return <VocabAdminPage title="Venue types" path="venue-types" />;
}
