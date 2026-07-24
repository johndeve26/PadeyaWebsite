"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchAdminPodJobs,
  markAdminPodJobFulfilled,
  retryAdminPodJob,
  type MerchPodJob,
} from "@/lib/merch-api";

export default function AdminPrintOnDemandPage() {
  const [jobs, setJobs] = useState<MerchPodJob[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const rows = await fetchAdminPodJobs();
    setJobs(rows);
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
              : "Failed to load print-on-demand jobs",
          );
          setJobs([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onFulfill(jobId: string) {
    setBusyId(jobId);
    setError(null);
    try {
      await markAdminPodJobFulfilled(jobId);
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
      await retryAdminPodJob(jobId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not retry job");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Print on demand"
      description="Provider-ready POD jobs across hosts. Created only after verified payment. Live Printful/Printify sync is still future."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/merchandise">
            <Button variant="secondary">Products</Button>
          </Link>
          <Link href="/admin/merchandise/orders">
            <Button variant="secondary">Orders</Button>
          </Link>
          <Link href="/admin">
            <Button variant="ghost">Admin home</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Load failed">
          {error}
        </Alert>
      ) : null}

      <div className="flex items-center gap-2">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">
          Jobs
        </h2>
        {jobs ? (
          <Badge tone="neutral" size="sm">
            {jobs.length}
          </Badge>
        ) : null}
      </div>

      {jobs === null ? (
        <SkeletonLoader lines={5} />
      ) : jobs.length === 0 ? (
        <EmptyState
          title="No POD jobs"
          description="Jobs appear after paid orders for print-on-demand products."
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
                  {job.manual_required ? (
                    <Badge tone="warning" size="sm">
                      Manual
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm text-foreground">
                  {job.status_label ||
                    job.error_note ||
                    "Print-on-demand job"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Host {job.host_id?.slice(0, 8) ?? "—"}… · Order{" "}
                  {job.order_id.slice(0, 8)}… · {formatDateTime(job.created_at)}
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
                {job.status !== "fulfilled" && job.status !== "cancelled" ? (
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
    </DashboardShell>
  );
}
