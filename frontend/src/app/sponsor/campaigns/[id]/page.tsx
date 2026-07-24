"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { SponsorCampaignRecommendations } from "@/components/sponsor/SponsorCampaignRecommendations";
import {
  Alert,
  Button,
  Container,
  DataTable,
  SectionHeader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import {
  activateSponsorCampaign,
  archiveSponsorCampaign,
  fetchSponsorCampaign,
  pauseSponsorCampaign,
  type SponsorCampaignDetail,
} from "@/lib/sponsor-campaigns-api";

export default function SponsorCampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const campaignId = params.id;

  const [campaign, setCampaign] = useState<SponsorCampaignDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!sponsorId || !campaignId) return;
    setCampaign(await fetchSponsorCampaign(sponsorId, campaignId));
  }, [campaignId, sponsorId]);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load campaign");
      }
    })();
  }, [load, sponsorId]);

  async function runAction(
    fn: () => Promise<SponsorCampaignDetail>,
  ): Promise<void> {
    setBusy(true);
    try {
      setCampaign(await fn());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!sponsorId) return null;

  return (
    <Container className="space-y-6 py-6">
      {campaign ? (
        <>
          <SectionHeader
            eyebrow="Campaign"
            title={campaign.name}
            description={campaign.description ?? undefined}
            action={
              <div className="flex flex-wrap gap-2">
                {campaign.can_edit ? (
                  <>
                    <Link href={`/sponsor/campaigns/${campaign.id}/edit`}>
                      <Button variant="secondary" size="sm">
                        Edit
                      </Button>
                    </Link>
                    <Link href={`/sponsor/campaigns/${campaign.id}/reports`}>
                      <Button variant="secondary" size="sm">
                        Reports
                      </Button>
                    </Link>
                    {campaign.status === "active" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() =>
                          void runAction(() =>
                            pauseSponsorCampaign(sponsorId, campaign.id),
                          )
                        }
                      >
                        Pause
                      </Button>
                    ) : null}
                    {["draft", "paused"].includes(campaign.status) ? (
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() =>
                          void runAction(() =>
                            activateSponsorCampaign(sponsorId, campaign.id),
                          )
                        }
                      >
                        Activate
                      </Button>
                    ) : null}
                    {campaign.status !== "archived" ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() =>
                          void runAction(async () => {
                            const archived = await archiveSponsorCampaign(
                              sponsorId,
                              campaign.id,
                            );
                            return archived;
                          })
                        }
                      >
                        Archive
                      </Button>
                    ) : null}
                  </>
                ) : null}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push("/sponsor/campaigns")}
                >
                  Back
                </Button>
              </div>
            }
          />
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={campaign.status} />
            <span className="rounded-md bg-muted px-2 py-1 text-xs capitalize">
              {campaign.objective.replace(/_/g, " ")}
            </span>
            <span className="rounded-md bg-muted px-2 py-1 text-xs">
              {campaign.visibility.replace(/_/g, " ")}
            </span>
          </div>
          {campaign.rejection_reason ? (
            <Alert tone="danger" title="Moderation">
              {campaign.rejection_reason}
            </Alert>
          ) : null}
          <section className="rounded-xl border border-border p-4">
            <h2 className="font-bold">Overview</h2>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2 text-sm">
              <div>
                <dt className="text-muted-foreground">Budget</dt>
                <dd>
                  {campaign.budget_min != null || campaign.budget_max != null
                    ? `${campaign.budget_min != null ? formatNgn(Number(campaign.budget_min)) : "—"} – ${campaign.budget_max != null ? formatNgn(Number(campaign.budget_max)) : "—"}`
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Dates</dt>
                <dd>
                  {campaign.start_date ?? "—"} → {campaign.end_date ?? "—"}
                </dd>
              </div>
            </dl>
          </section>
          <section className="rounded-xl border border-border p-4">
            <h2 className="font-bold">Targeting</h2>
            <ul className="mt-2 list-inside list-disc text-sm text-muted-foreground">
              <li>
                Categories:{" "}
                {(campaign.target_categories ?? []).join(", ") || "—"}
              </li>
              <li>
                Locations: {(campaign.target_locations ?? []).join(", ") || "—"}
              </li>
              <li>
                Audience:{" "}
                {campaign.target_audience
                  ? JSON.stringify(campaign.target_audience)
                  : "—"}
              </li>
            </ul>
          </section>
          <section className="space-y-3">
            <h2 className="font-bold">Recommended opportunities</h2>
            <p className="text-sm text-muted-foreground">
              Rules-based matches for this campaign on Pàdéyá — no AI ranking and no
              auto-contact.
            </p>
            <SponsorCampaignRecommendations
              sponsorId={sponsorId}
              campaignId={campaign.id}
              canEdit={campaign.can_edit}
            />
          </section>
          <section className="space-y-3">
            <h2 className="font-bold">Saved opportunities</h2>
            {campaign.saved_items.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No saved items linked. Add from{" "}
                <Link href="/sponsor/saved" className="text-accent underline">
                  Saved
                </Link>
                .
              </p>
            ) : (
              <ul className="space-y-2">
                {campaign.saved_items.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-lg border border-border px-3 py-2 text-sm"
                  >
                    {item.available && item.href ? (
                      <Link href={item.href} className="font-semibold text-accent">
                        {item.title}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">Unavailable</span>
                    )}
                    {item.note ? (
                      <p className="text-muted-foreground">{item.note}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="space-y-3">
            <h2 className="font-bold">Related inquiries</h2>
            <DataTable
              columns={[
                {
                  key: "host",
                  header: "Host",
                  cell: (r) => r.host_display_name ?? "—",
                  primary: true,
                },
                { key: "slot", header: "Slot", cell: (r) => r.slot_title ?? "—" },
                { key: "status", header: "Status", cell: (r) => r.status },
                {
                  key: "sent",
                  header: "Sent",
                  cell: (r) => formatDateTime(r.created_at),
                },
              ]}
              rows={campaign.inquiries}
              rowKey={(r) => r.id}
              emptyTitle="No inquiries linked to this campaign yet."
            />
          </section>
        </>
      ) : error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : (
        <p className="text-muted-foreground">Loading…</p>
      )}
    </Container>
  );
}
