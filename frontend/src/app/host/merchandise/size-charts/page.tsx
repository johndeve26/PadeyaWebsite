"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  SectionHeader,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  archiveHostSizeChart,
  createHostSizeChart,
  fetchHostSizeCharts,
  updateHostSizeChart,
} from "@/lib/merch-api";
import {
  CAP_CHART_EXAMPLE,
  TEE_CHART_EXAMPLE,
  type MerchSizeChart,
} from "@/lib/merch-size-chart";
import { MERCH_PRODUCT_TYPES } from "@/lib/merch-product-types";

const EXAMPLE_JSON = JSON.stringify(TEE_CHART_EXAMPLE, null, 2);

export default function HostMerchSizeChartsPage() {
  const [rows, setRows] = useState<MerchSizeChart[]>([]);
  const [name, setName] = useState("");
  const [productType, setProductType] = useState("t_shirt");
  const [units, setUnits] = useState("cm");
  const [fitNotes, setFitNotes] = useState("");
  const [chartJsonText, setChartJsonText] = useState(EXAMPLE_JSON);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    setRows(await fetchHostSizeCharts());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load size charts",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  function applyTeeExample() {
    setProductType("t_shirt");
    setChartJsonText(JSON.stringify(TEE_CHART_EXAMPLE, null, 2));
    if (!name.trim()) setName("Unisex tee — standard");
  }

  function applyCapExample() {
    setProductType("cap");
    setChartJsonText(JSON.stringify(CAP_CHART_EXAMPLE, null, 2));
    if (!name.trim()) setName("Cap — one size");
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      let chart_json: unknown;
      try {
        chart_json = JSON.parse(chartJsonText);
      } catch {
        setError("chart_json must be valid JSON");
        return;
      }
      await createHostSizeChart({
        name,
        product_type: productType || null,
        units,
        chart_json,
        fit_notes: fitNotes.trim() || null,
      });
      setName("");
      setFitNotes("");
      setChartJsonText(EXAMPLE_JSON);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(row: MerchSizeChart) {
    try {
      await updateHostSizeChart(row.id, {
        status: row.status === "active" ? "inactive" : "active",
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function onArchive(row: MerchSizeChart) {
    try {
      await archiveHostSizeChart(row.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Archive failed");
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Size charts"
        description="Reusable size guides for Pàdéyá merch. Attach a chart when editing a product."
        actions={
          <Link href="/host/merchandise">
            <Button size="sm" variant="secondary">
              Back to merch
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <Card className="mb-8 max-w-2xl space-y-4">
          <SectionHeader
            title="Create size chart"
            description="Use columns × rows JSON. Tees usually include Size, Chest, Length, Sleeve; caps can be one size."
          />
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="secondary" onClick={applyTeeExample}>
              Tee example
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={applyCapExample}>
              Cap example
            </Button>
          </div>
          <pre className="overflow-x-auto rounded-[var(--radius-md)] border border-border bg-surface-muted p-3 text-xs text-muted-foreground">
            {`{
  "columns": ["Size", "Chest", "Length", "Sleeve"],
  "rows": [
    ["S", "96", "68", "20"],
    ["M", "102", "70", "21"]
  ]
}`}
          </pre>
          <form className="space-y-4" onSubmit={onCreate}>
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Unisex tee — standard"
              required
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Select
                label="Product type"
                value={productType}
                onChange={(e) => setProductType(e.target.value)}
              >
                {MERCH_PRODUCT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </Select>
              <Select
                label="Units"
                value={units}
                onChange={(e) => setUnits(e.target.value)}
              >
                <option value="cm">cm</option>
                <option value="inches">inches</option>
              </Select>
            </div>
            <Textarea
              label="Fit notes"
              rows={2}
              value={fitNotes}
              onChange={(e) => setFitNotes(e.target.value)}
              placeholder="Runs true to size. Measure chest under arms."
            />
            <Textarea
              label="chart_json"
              rows={10}
              value={chartJsonText}
              onChange={(e) => setChartJsonText(e.target.value)}
              hint="Object with columns (string[]) and rows (cell[][])."
              className="font-mono text-xs"
            />
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Create chart"}
            </Button>
          </form>
        </Card>

        <Card className="space-y-4">
          <SectionHeader
            title="Your charts"
            description="Inactive charts stay in the host list but are hidden from buyers."
          />
          {rows.length === 0 ? (
            <EmptyState
              title="No size charts yet"
              description="Create a reusable guide, then attach it on a product."
            />
          ) : (
            <ul className="divide-y divide-border">
              {rows.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-4"
                >
                  <div className="min-w-0 space-y-1">
                    <p className="font-semibold text-foreground">{row.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {row.product_type || "any type"} · {row.units}
                      {row.fit_notes ? ` · ${row.fit_notes}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      tone={row.status === "active" ? "success" : "neutral"}
                      size="sm"
                    >
                      {row.status}
                    </Badge>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void toggleActive(row)}
                    >
                      {row.status === "active" ? "Deactivate" : "Activate"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void onArchive(row)}
                    >
                      Archive
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
