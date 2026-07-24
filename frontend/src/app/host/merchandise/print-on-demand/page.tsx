"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Select,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchHostPodIntegrations,
  fetchHostPodJobs,
  markHostPodJobFulfilled,
  retryHostPodJob,
  upsertHostPodIntegration,
  type MerchPodIntegration,
  type MerchPodJob,
} from "@/lib/merch-api";

const PROVIDERS = [
  { value: "manual", label: "Manual" },
  { value: "printful", label: "Printful (placeholder)" },
  { value: "printify", label: "Printify (placeholder)" },
  { value: "custom", label: "Custom (placeholder)" },
] as const;

const STATUSES = [
  { value: "disabled", label: "Disabled" },
  { value: "connected", label: "Connected" },
  { value: "error", label: "Error" },
] as const;

export default function HostPrintOnDemandPage() {
  const [jobs, setJobs] = useState<MerchPodJob[] | null>(null);
  const [integrations, setIntegrations] = useState<MerchPodIntegration[]>([]);
  const [provider, setProvider] = useState("manual");
  const [status, setStatus] = useState("connected");
  const [storeRef, setStoreRef] = useState("");
  const [credentials, setCredentials] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const [jobRows, integrationRows] = await Promise.all([
      fetchHostPodJobs(),
      fetchHostPodIntegrations(),
    ]);
    setJobs(jobRows);
    setIntegrations(integrationRows);
    const primary = integrationRows[0];
    if (primary) {
      setProvider(primary.provider);
      setStatus(primary.status);
      setStoreRef(primary.provider_store_ref ?? "");
    }
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Failed to load print-on-demand",
          );
          setJobs([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onSaveIntegration(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      await upsertHostPodIntegration({
        provider,
        status,
        provider_store_ref: storeRef.trim() || null,
        credentials: credentials.trim() || null,
      });
      setCredentials("");
      setNote(
        provider === "manual"
          ? "Manual POD settings saved."
          : "Provider settings saved. Live Printful/Printify sync is still future.",
      );
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not save integration",
      );
    } finally {
      setSaving(false);
    }
  }

  async function onFulfill(jobId: string) {
    setBusyId(jobId);
    setError(null);
    try {
      await markHostPodJobFulfilled(jobId);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not mark job fulfilled",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function onRetry(jobId: string) {
    setBusyId(jobId);
    setError(null);
    try {
      await retryHostPodJob(jobId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not retry job");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Print on demand"
        description="Provider-ready POD on Pàdéyá. Jobs are created only after verified payment. Live Printful/Printify sync is still future — fulfill manually for now."
        actions={
          <Link href="/host/merchandise">
            <Button size="sm" variant="secondary">
              Merchandise
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Print on demand">
            {error}
          </Alert>
        ) : null}
        {note ? (
          <Alert tone="success" title="Saved">
            {note}
          </Alert>
        ) : null}

        <Card className="space-y-4">
          <div>
            <h2 className="text-base font-extrabold text-foreground">
              Integration settings
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Choose a provider and connection status. Credentials are encrypted
              when stored and never shown again.
            </p>
          </div>
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={onSaveIntegration}>
            <Select
              label="Provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              {PROVIDERS.map((row) => (
                <option key={row.value} value={row.value}>
                  {row.label}
                </option>
              ))}
            </Select>
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUSES.map((row) => (
                <option key={row.value} value={row.value}>
                  {row.label}
                </option>
              ))}
            </Select>
            <Input
              label="Provider store ref"
              value={storeRef}
              onChange={(e) => setStoreRef(e.target.value)}
              placeholder="Optional store / shop id"
            />
            <Input
              label="Credentials"
              type="password"
              value={credentials}
              onChange={(e) => setCredentials(e.target.value)}
              placeholder="Leave blank to keep existing"
              autoComplete="off"
            />
            <div className="sm:col-span-2">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving…" : "Save integration"}
              </Button>
            </div>
          </form>
          {integrations.length > 0 ? (
            <ul className="divide-y divide-border border-t border-border">
              {integrations.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
                >
                  <div>
                    <p className="font-bold text-foreground">{row.provider}</p>
                    <p className="text-muted-foreground">
                      {row.sync_note || "No sync note"}
                      {row.has_credentials ? " · credentials stored" : ""}
                    </p>
                  </div>
                  <StatusBadge status={row.status} />
                </li>
              ))}
            </ul>
          ) : null}
        </Card>

        <Card className="space-y-4">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-extrabold text-foreground">
              POD jobs
            </h2>
            {jobs ? (
              <Badge tone="neutral" size="sm">
                {jobs.length}
              </Badge>
            ) : null}
          </div>
          {jobs === null ? (
            <SkeletonLoader lines={4} />
          ) : jobs.length === 0 ? (
            <EmptyState
              title="No POD jobs yet"
              description="Jobs appear here after a buyer pays for a print-on-demand product."
            />
          ) : (
            <ul className="divide-y divide-border border-y border-border">
              {jobs.map((job) => (
                <li
                  key={job.id}
                  className="flex flex-wrap items-start justify-between gap-3 py-3"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={job.status} />
                      <span className="text-sm font-bold text-foreground">
                        {job.provider}
                      </span>
                    </div>
                    <p className="text-sm text-foreground">
                      {job.status_label ||
                        job.error_note ||
                        "Print-on-demand job"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Order {job.order_id.slice(0, 8)}… ·{" "}
                      {formatDateTime(job.created_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {job.status === "failed" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busyId === job.id}
                        onClick={() => void onRetry(job.id)}
                      >
                        Retry
                      </Button>
                    ) : null}
                    {job.status !== "fulfilled" &&
                    job.status !== "cancelled" ? (
                      <Button
                        size="sm"
                        disabled={busyId === job.id}
                        onClick={() => void onFulfill(job.id)}
                      >
                        Mark fulfilled
                      </Button>
                    ) : null}
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
