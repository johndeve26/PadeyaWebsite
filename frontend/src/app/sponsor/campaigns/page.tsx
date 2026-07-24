"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import {
  Alert,
  Button,
  Container,
  EmptyState,
  SectionHeader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import {
  fetchSponsorCampaigns,
  type SponsorCampaignListItem,
} from "@/lib/sponsor-campaigns-api";

function canManage(active: { is_owner: boolean; role: string } | null): boolean {
  if (!active) return false;
  return (
    active.is_owner ||
    active.role === "admin" ||
    active.role === "campaign_manager"
  );
}

function budgetLabel(row: SponsorCampaignListItem): string {
  if (row.budget_min == null && row.budget_max == null) return "—";
  if (row.budget_min != null && row.budget_max != null) {
    return `${formatNgn(Number(row.budget_min))} – ${formatNgn(Number(row.budget_max))}`;
  }
  if (row.budget_max != null) return `Up to ${formatNgn(Number(row.budget_max))}`;
  return `From ${formatNgn(Number(row.budget_min))}`;
}

export default function SponsorCampaignsPage() {
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const manageable = canManage(
    active ? { is_owner: active.is_owner, role: active.role } : null,
  );

  const [items, setItems] = useState<SponsorCampaignListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!sponsorId) return;
    const data = await fetchSponsorCampaigns(sponsorId);
    setItems(data.items);
  }, [sponsorId]);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load campaigns");
      }
    })();
  }, [load, sponsorId]);

  if (!sponsorId) return null;

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Manage"
        title="Campaigns"
        description="Organize sponsorship goals, budget, saved opportunities, and inquiries on Pàdéyá. Private workspace data stays off public profiles."
        action={
          manageable ? (
            <Link href="/sponsor/campaigns/new">
              <Button>New campaign</Button>
            </Link>
          ) : null
        }
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      {items.length === 0 ? (
        <EmptyState
          title="No campaigns yet"
          description={
            manageable
              ? "Create a campaign to group saved hosts, events, and marketplace inquiries."
              : "Your team has not created campaigns yet."
          }
        />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {items.map((row) => (
            <li
              key={row.id}
              className="rounded-xl border border-border bg-card p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <Link
                  href={`/sponsor/campaigns/${row.id}`}
                  className="text-lg font-bold text-accent hover:underline"
                >
                  {row.name}
                </Link>
                <StatusBadge status={row.status} />
              </div>
              <p className="mt-1 text-sm capitalize text-muted-foreground">
                {row.objective.replace(/_/g, " ")}
              </p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <dt className="text-muted-foreground">Budget</dt>
                  <dd className="font-medium">{budgetLabel(row)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Dates</dt>
                  <dd className="font-medium">
                    {row.start_date ?? "—"} → {row.end_date ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Saved</dt>
                  <dd className="font-medium">{row.saved_items_count}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Inquiries</dt>
                  <dd className="font-medium">{row.inquiries_count}</dd>
                </div>
              </dl>
              <p className="mt-2 text-xs text-muted-foreground">
                Updated {formatDateTime(row.updated_at)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Container>
  );
}
