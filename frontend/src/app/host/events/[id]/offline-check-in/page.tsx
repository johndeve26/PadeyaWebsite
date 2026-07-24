"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

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
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { syncOfflineScans } from "@/lib/advanced-tickets-api";
import type { OfflineSyncResult } from "@/lib/types/advanced-tickets";
import { cn } from "@/lib/cn";

const STORAGE_KEY_PREFIX = "padeya.offline_scans.";

type LocalScan = {
  client_scan_id: string;
  public_code: string;
  scanned_at: string;
};

function loadLocal(eventId: string): LocalScan[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${eventId}`);
    return raw ? (JSON.parse(raw) as LocalScan[]) : [];
  } catch {
    return [];
  }
}

function saveLocal(eventId: string, scans: LocalScan[]) {
  localStorage.setItem(`${STORAGE_KEY_PREFIX}${eventId}`, JSON.stringify(scans));
}

function syncStatusTone(
  status: string,
): "success" | "warning" | "danger" | "neutral" {
  if (status === "accepted" || status === "success") return "success";
  if (status === "conflict" || status === "duplicate") return "warning";
  if (status === "invalid") return "danger";
  return "neutral";
}

function SyncResultPanel({ result }: { result: OfflineSyncResult }) {
  return (
    <section className="space-y-4">
      <SectionHeader
        eyebrow="Sync complete"
        title="Last sync results"
        description="Accepted scans are recorded. Conflicts mean the ticket was already checked in."
      />
      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="border-2 border-accent bg-[color-mix(in_srgb,var(--brand-green)_8%,transparent)] text-center">
          <p className="text-3xl font-extrabold text-foreground">
            {result.accepted_count}
          </p>
          <Badge tone="success" className="mt-2">
            Accepted
          </Badge>
        </Card>
        <Card className="border-2 border-warning-border bg-warning-soft/40 text-center">
          <p className="text-3xl font-extrabold text-foreground">
            {result.conflict_count}
          </p>
          <Badge tone="warning" className="mt-2">
            Conflicts
          </Badge>
        </Card>
        <Card className="border-2 border-danger-border bg-danger-soft/50 text-center">
          <p className="text-3xl font-extrabold text-foreground">
            {result.invalid_count}
          </p>
          <Badge tone="danger" className="mt-2">
            Invalid
          </Badge>
        </Card>
      </div>
      {result.results.length > 0 ? (
        <Card className="divide-y divide-border p-0">
          {result.results.map((r) => (
            <div
              key={r.client_scan_id}
              className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="truncate font-mono text-sm font-semibold text-foreground">
                  {r.ticket?.public_code ?? r.client_scan_id}
                </p>
                {r.conflict_reason ? (
                  <p className="text-xs text-muted-foreground">{r.conflict_reason}</p>
                ) : null}
              </div>
              <Badge tone={syncStatusTone(r.sync_status)}>{r.sync_status}</Badge>
            </div>
          ))}
        </Card>
      ) : null}
    </section>
  );
}

export default function OfflineCheckInPage() {
  const params = useParams<{ id: string }>();
  const [scans, setScans] = useState<LocalScan[]>(() => loadLocal(params.id));
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OfflineSyncResult | null>(null);
  const [busy, setBusy] = useState(false);

  function addScan() {
    const public_code = code.trim();
    if (!public_code) return;
    const next: LocalScan[] = [
      ...scans,
      {
        client_scan_id: `local-${scans.length + 1}-${public_code}`,
        public_code,
        scanned_at: new Date().toISOString(),
      },
    ];
    setScans(next);
    saveLocal(params.id, next);
    setCode("");
  }

  function clearBuffer() {
    setScans([]);
    saveLocal(params.id, []);
  }

  async function onSync() {
    setBusy(true);
    setError(null);
    setResult(null);
    const batchId = `offline-${params.id.slice(0, 8)}-${scans.length}-${scans[0]?.client_scan_id ?? "empty"}`;
    try {
      const body = await syncOfflineScans({
        event_id: params.id,
        client_batch_id: batchId,
        device_label: "Host offline buffer",
        scans: scans.map((s) => ({
          client_scan_id: s.client_scan_id,
          public_code: s.public_code,
          scanned_at: s.scanned_at,
        })),
      });
      setResult(body);
      setScans([]);
      saveLocal(params.id, []);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Offline check-in"
        title="Offline scan buffer"
        description="Store scans locally when connectivity is poor, then sync when you're back online. Conflicts are reported when a ticket was already checked in."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={`/host/events/${params.id}/check-in`}>
              <Button size="sm">Live check-in</Button>
            </Link>
            <Link href={`/host/events/${params.id}/tables`}>
              <Button size="sm" variant="secondary">
                Tables
              </Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Sync error">
            {error}
          </Alert>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
          <Card className="space-y-4">
            <SectionHeader
              title="Capture scan"
              description="Enter a ticket public code to queue it locally."
            />
            <Input
              label="Ticket public code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="PDY-…"
              autoComplete="off"
              inputMode="text"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addScan();
                }
              }}
            />
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
              <Button
                onClick={addScan}
                disabled={!code.trim()}
                className="w-full sm:w-auto"
              >
                Store locally
              </Button>
              <Button
                variant="secondary"
                disabled={busy || scans.length === 0}
                onClick={() => void onSync()}
                className="w-full sm:w-auto"
              >
                {busy ? "Syncing…" : `Sync ${scans.length} scan(s)`}
              </Button>
            </div>
          </Card>

          <section className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <SectionHeader
                title="Local buffer"
                description="Scans waiting to upload from this device."
              />
              <div className="flex items-center gap-2">
                <Badge tone={scans.length > 0 ? "accent" : "neutral"}>
                  {scans.length} queued
                </Badge>
                {scans.length > 0 ? (
                  <Button size="sm" variant="ghost" onClick={clearBuffer}>
                    Clear
                  </Button>
                ) : null}
              </div>
            </div>
            {scans.length === 0 ? (
              <EmptyState
                title="Buffer empty"
                description="No offline scans stored on this device. Capture codes above when the door has no signal."
              />
            ) : (
              <div className="space-y-2">
                {scans.map((s, i) => (
                  <Card
                    key={s.client_scan_id}
                    className={cn(
                      "flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between",
                      i === scans.length - 1 && "ring-2 ring-accent/30",
                    )}
                  >
                    <p className="font-mono text-sm font-bold tracking-wide text-foreground">
                      {s.public_code}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(s.scanned_at)}
                    </p>
                  </Card>
                ))}
              </div>
            )}
          </section>
        </div>

        {result ? (
          <div className="mt-8">
            <SyncResultPanel result={result} />
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
