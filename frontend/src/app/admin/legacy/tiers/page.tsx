"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  Input,
  SectionHeader,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchAdminLegacyTiers, updateAdminLegacyTier } from "@/lib/legacy-api";
import type { LegacyTier } from "@/lib/types/legacy";

export default function AdminLegacyTiersPage() {
  const [tiers, setTiers] = useState<LegacyTier[]>([]);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchAdminLegacyTiers();
        if (!active) return;
        setTiers(items);
        setScores(
          Object.fromEntries(items.map((t) => [t.id, String(t.min_score)])),
        );
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load tiers");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onSave(tier: LegacyTier) {
    setError(null);
    setBusyId(tier.id);
    try {
      const updated = await updateAdminLegacyTier(tier.id, {
        min_score: Number(scores[tier.id]),
      });
      setTiers((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setNote(`Updated ${updated.name} threshold`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Tier thresholds"
      description="Edit minimum composite scores for each Legacy tier. Recalculate hosts afterward."
      actions={
        <Link href="/admin/legacy">
          <Button variant="secondary">Back to host tiers</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Update failed">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone="success" title="Saved">
          {note}
        </Alert>
      ) : null}

      <Alert tone="info" title="After saving">
        Run <strong>Recalculate all hosts</strong> on the host tiers page so existing scores
        reflect new thresholds.
      </Alert>

      {loading && !error ? <SkeletonLoader lines={4} /> : null}

      {!loading ? (
      <div className="space-y-4">
        {tiers.map((tier) => (
          <Card key={tier.id} className="space-y-4">
            <SectionHeader
              eyebrow={tier.slug}
              title={tier.name}
              description={tier.description ?? undefined}
            />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <Input
                label="Minimum composite score"
                hint="0–100. Hosts at or above this score qualify for the tier."
                type="number"
                min={0}
                max={100}
                step="0.01"
                value={scores[tier.id] ?? ""}
                onChange={(e) =>
                  setScores((prev) => ({ ...prev, [tier.id]: e.target.value }))
                }
              />
              <Button
                disabled={busyId === tier.id}
                onClick={() => void onSave(tier)}
              >
                {busyId === tier.id ? "Saving…" : "Save threshold"}
              </Button>
            </div>
          </Card>
        ))}
      </div>
      ) : null}
    </DashboardShell>
  );
}
