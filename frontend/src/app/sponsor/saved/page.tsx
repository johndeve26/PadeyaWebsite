"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import {
  Alert,
  Button,
  Container,
  EmptyState,
  FilterBar,
  SectionHeader,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchSponsorSaved,
  unsaveSponsorItem,
  updateSponsorSavedNote,
  type SponsorSavedItem,
} from "@/lib/sponsor-saved-api";
import {
  addSavedItemToCampaign,
  fetchSponsorCampaigns,
  type SponsorCampaignListItem,
} from "@/lib/sponsor-campaigns-api";

const TYPE_OPTIONS = [
  { value: "all", label: "All types" },
  { value: "host", label: "Hosts" },
  { value: "event", label: "Events" },
  { value: "sponsorship_slot", label: "Opportunities" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest saved" },
  { value: "event_date", label: "Event date" },
  { value: "host_name", label: "Host name" },
];

function canEditNotes(active: {
  is_owner: boolean;
  role: string;
} | null): boolean {
  if (!active) return false;
  return (
    active.is_owner ||
    active.role === "admin" ||
    active.role === "campaign_manager"
  );
}

export default function SponsorSavedPage() {
  const { active } = useSponsorWorkspace();
  const sponsorId = active?.sponsor_id ?? null;
  const editable = canEditNotes(
    active ? { is_owner: active.is_owner, role: active.role } : null,
  );

  const [items, setItems] = useState<SponsorSavedItem[]>([]);
  const [savedCount, setSavedCount] = useState(0);
  const [typeFilter, setTypeFilter] = useState("all");
  const [sort, setSort] = useState("newest");
  const [error, setError] = useState<string | null>(null);
  const [noteDraft, setNoteDraft] = useState<Record<string, string>>({});
  const [campaigns, setCampaigns] = useState<SponsorCampaignListItem[]>([]);
  const [campaignPick, setCampaignPick] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    if (!sponsorId) return;
    const data = await fetchSponsorSaved(sponsorId, {
      item_type: typeFilter === "all" ? undefined : typeFilter,
      sort,
    });
    setItems(data.items);
    setSavedCount(data.saved_count);
    if (editable) {
      const c = await fetchSponsorCampaigns(sponsorId);
      setCampaigns(c.items.filter((row) => row.status !== "archived"));
    }
  }, [sponsorId, sort, typeFilter, editable]);

  useEffect(() => {
    if (!sponsorId) return;
    void (async () => {
      try {
        await load();
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load saved items");
      }
    })();
  }, [load, sponsorId]);

  const visible = useMemo(
    () => items.filter((i) => i.available || i.note),
    [items],
  );

  if (!sponsorId) return null;

  return (
    <Container className="space-y-6 py-6">
      <SectionHeader
        eyebrow="Workspace"
        title="Saved"
        description={`${savedCount} saved hosts, events, and opportunities in your private list. No auto-contact — notes are for your team only.`}
        action={
          <Link href="/sponsor/opportunities">
            <Button variant="secondary">Browse opportunities</Button>
          </Link>
        }
      />
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}
      <FilterBar>
        <Select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by type"
        >
          {TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          aria-label="Sort saved"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </FilterBar>
      {visible.length === 0 ? (
        <EmptyState
          title="Nothing saved yet"
          description="Save hosts, events, or sponsorship slots from the marketplace."
        />
      ) : (
        <ul className="space-y-4">
          {visible.map((row) => (
            <li
              key={row.id}
              className="rounded-xl border border-border bg-card p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    {row.item_type.replace("_", " ")}
                  </p>
                  {row.available && row.title ? (
                    <Link
                      href={row.href ?? "#"}
                      className="text-lg font-bold text-accent hover:underline"
                    >
                      {row.title}
                    </Link>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No longer publicly available
                    </p>
                  )}
                  {row.subtitle ? (
                    <p className="text-sm text-muted-foreground">{row.subtitle}</p>
                  ) : null}
                  <p className="text-xs text-muted-foreground">
                    Saved {formatDateTime(row.created_at)}
                  </p>
                </div>
                {editable ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      void (async () => {
                        try {
                          await unsaveSponsorItem(sponsorId, row.id);
                          await load();
                        } catch (err) {
                          setError(
                            err instanceof ApiError ? err.detail : "Unsave failed",
                          );
                        }
                      })()
                    }
                  >
                    Unsave
                  </Button>
                ) : null}
              </div>
              {editable && campaigns.length > 0 ? (
                <div className="mt-2 flex flex-wrap items-end gap-2">
                  <label className="text-sm">
                    <span className="font-semibold">Add to campaign</span>
                    <Select
                      className="mt-1 block"
                      value={campaignPick[row.id] ?? ""}
                      onChange={(e) =>
                        setCampaignPick((d) => ({
                          ...d,
                          [row.id]: e.target.value,
                        }))
                      }
                    >
                      <option value="">Select campaign</option>
                      {campaigns.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={!campaignPick[row.id]}
                    onClick={() =>
                      void (async () => {
                        const cid = campaignPick[row.id];
                        if (!cid) return;
                        try {
                          await addSavedItemToCampaign(sponsorId, cid, row.id);
                          setError(null);
                        } catch (err) {
                          setError(
                            err instanceof ApiError
                              ? err.detail
                              : "Could not add to campaign",
                          );
                        }
                      })()
                    }
                  >
                    Add
                  </Button>
                  <Link
                    href={`/sponsor/campaigns/new?saved_item_id=${row.id}`}
                    className="text-sm text-accent underline"
                  >
                    New campaign from this
                  </Link>
                </div>
              ) : editable ? (
                <Link
                  href={`/sponsor/campaigns/new?saved_item_id=${row.id}`}
                  className="mt-2 inline-block text-sm text-accent underline"
                >
                  Create campaign from saved item
                </Link>
              ) : null}
              {editable ? (
                <label className="mt-3 block space-y-1 text-sm">
                  <span className="font-semibold">Private note</span>
                  <Textarea
                    value={noteDraft[row.id] ?? row.note ?? ""}
                    onChange={(e) =>
                      setNoteDraft((d) => ({ ...d, [row.id]: e.target.value }))
                    }
                    placeholder="Internal note for your sponsor team"
                  />
                  {(noteDraft[row.id] ?? row.note ?? "") !== (row.note ?? "") ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        void (async () => {
                          try {
                            await updateSponsorSavedNote(
                              sponsorId,
                              row.id,
                              noteDraft[row.id] ?? null,
                            );
                            await load();
                          } catch (err) {
                            setError(
                              err instanceof ApiError ? err.detail : "Note save failed",
                            );
                          }
                        })()
                      }
                    >
                      Save note
                    </Button>
                  ) : null}
                </label>
              ) : row.note ? (
                <p className="mt-2 text-sm text-muted-foreground">{row.note}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Container>
  );
}
