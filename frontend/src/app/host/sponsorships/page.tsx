"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { HostSponsorshipPitchAIAssist } from "@/components/host/sponsorships/HostSponsorshipPitchAIAssist";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { SponsorHowItWorks, SponsorSlotCard } from "@/components/sponsors";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  Input,
  SectionHeader,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { canManageSponsorshipSlots } from "@/lib/host-access";
import {
  SPONSORSHIP_HOSTS_PATH,
  SPONSORSHIP_MARKETPLACE_PATH,
} from "@/lib/sponsor-marketplace-paths";
import {
  SPONSORSHIP_SLOT_FILTERS,
  SPONSORSHIP_SLOT_TYPES,
  type SponsorshipSlotFilter,
} from "@/lib/sponsorship-slot-form";
import {
  fetchHostInquiries,
  fetchHostPlacements,
  fetchHostSponsorshipSettings,
  fetchHostSponsorshipSlots,
  updateHostInquiry,
  updateHostSponsorshipSettings,
  updateSponsorshipSlot,
} from "@/lib/sponsorships-api";
import type {
  HostSponsorshipSettings,
  SponsorshipInquiry,
  SponsorshipPlacement,
  SponsorshipSlot,
} from "@/lib/types/sponsorships";

export default function HostSponsorshipsPage() {
  const { active } = useHostWorkspace();
  const canManage = canManageSponsorshipSlots(active);
  const [settings, setSettings] = useState<HostSponsorshipSettings | null>(null);
  const [slots, setSlots] = useState<SponsorshipSlot[]>([]);
  const [inquiries, setInquiries] = useState<SponsorshipInquiry[]>([]);
  const [placements, setPlacements] = useState<SponsorshipPlacement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [slotFilter, setSlotFilter] = useState<SponsorshipSlotFilter>("all");
  const [pitch, setPitch] = useState("");
  const [audienceNotes, setAudienceNotes] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [savingSettings, setSavingSettings] = useState(false);
  const [aiSlotType, setAiSlotType] = useState("logo_event_page");
  const [aiNotes, setAiNotes] = useState("");

  function applySettings(s: HostSponsorshipSettings) {
    setSettings(s);
    setPitch(s.pitch || "");
    setAudienceNotes(s.audience_notes || "");
    setContactEmail(s.contact_email || "");
  }

  async function load() {
    const [s, sl, iq, pl] = await Promise.all([
      fetchHostSponsorshipSettings(),
      fetchHostSponsorshipSlots(),
      fetchHostInquiries(),
      fetchHostPlacements(),
    ]);
    applySettings(s);
    setSlots(sl);
    setInquiries(iq);
    setPlacements(pl);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [s, sl, iq, pl] = await Promise.all([
          fetchHostSponsorshipSettings(),
          fetchHostSponsorshipSlots(),
          fetchHostInquiries(),
          fetchHostPlacements(),
        ]);
        if (!active) return;
        applySettings(s);
        setSlots(sl);
        setInquiries(iq);
        setPlacements(pl);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const slotCounts = useMemo(() => {
    const counts: Record<SponsorshipSlotFilter, number> = {
      all: slots.length,
      draft: 0,
      published: 0,
      disabled: 0,
    };
    for (const slot of slots) {
      const status = (slot.status || "").toLowerCase();
      if (status === "draft") counts.draft += 1;
      else if (status === "published") counts.published += 1;
      else if (status === "disabled") counts.disabled += 1;
    }
    return counts;
  }, [slots]);

  const visibleSlots = useMemo(() => {
    if (slotFilter === "all") return slots;
    return slots.filter(
      (slot) => (slot.status || "").toLowerCase() === slotFilter,
    );
  }, [slots, slotFilter]);

  async function toggleAccepting() {
    if (!settings) return;
    setNote(null);
    try {
      const updated = await updateHostSponsorshipSettings({
        accepting_sponsors: !settings.accepting_sponsors,
      });
      applySettings(updated);
      setNote("Settings saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function savePitchSettings() {
    setSavingSettings(true);
    setNote(null);
    setError(null);
    try {
      const updated = await updateHostSponsorshipSettings({
        pitch: pitch.trim(),
        audience_notes: audienceNotes.trim(),
        contact_email: contactEmail.trim() || undefined,
      });
      applySettings(updated);
      setNote("Host pitch saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    } finally {
      setSavingSettings(false);
    }
  }

  async function setSlotStatus(id: string, status: string, successNote: string) {
    setError(null);
    setNote(null);
    try {
      await updateSponsorshipSlot(id, { status });
      await load();
      setNote(successNote);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function setInquiryStatus(id: string, status: string) {
    try {
      await updateHostInquiry(id, { status });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  function slotActions(slot: SponsorshipSlot) {
    if (!canManage) return null;
    const status = (slot.status || "").toLowerCase();
    return (
      <div className="flex flex-wrap gap-2">
        <Link href={`/host/sponsorships/${slot.id}/edit`}>
          <Button size="sm" variant="secondary">
            Edit
          </Button>
        </Link>
        {status === "draft" || status === "disabled" ? (
          <Button
            size="sm"
            onClick={() =>
              void setSlotStatus(
                slot.id,
                "published",
                "Slot published (requires verified host).",
              )
            }
          >
            Publish
          </Button>
        ) : null}
        {status === "published" ? (
          <Button
            size="sm"
            variant="secondary"
            onClick={() =>
              void setSlotStatus(slot.id, "draft", "Slot moved back to draft.")
            }
          >
            Unpublish
          </Button>
        ) : null}
        {status !== "disabled" ? (
          <ConfirmAction
            label="Delete"
            title="Delete this sponsorship slot?"
            description="The package is removed from the marketplace. You can restore it later from the Disabled filter."
            confirmLabel="Delete slot"
            tone="danger"
            size="sm"
            variant="ghost"
            onConfirm={() =>
              setSlotStatus(
                slot.id,
                "disabled",
                "Slot deleted — hidden from the marketplace.",
              )
            }
          />
        ) : (
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              void setSlotStatus(slot.id, "draft", "Slot restored as draft.")
            }
          >
            Restore
          </Button>
        )}
      </div>
    );
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Sponsorships"
        title="Attract brands with clear packages"
        description="List what brands will see on Pàdéyá: verified host status, open slots, pricing, and your pitch. Publishing requires a verified host — it does not approve events."
        actions={
          <div className="flex flex-wrap gap-3">
            {canManage ? (
              <Link href="/host/sponsorships/new">
                <Button>New slot</Button>
              </Link>
            ) : null}
            <Link href={SPONSORSHIP_MARKETPLACE_PATH}>
              <Button variant="secondary">Public marketplace</Button>
            </Link>
            {canManage && settings ? (
              <Button variant="ghost" onClick={() => void toggleAccepting()}>
                {settings.accepting_sponsors
                  ? "Accepting sponsors: On"
                  : "Accepting sponsors: Off"}
              </Button>
            ) : null}
          </div>
        }
      >
        {!canManage ? (
          <Alert tone="info" title="Read-only sponsor desk">
            You can review slots, inquiries, and placements here. Creating slots
            or editing host pitch requires manage sponsorship permissions.
          </Alert>
        ) : null}
        {error ? (
          <Alert tone="danger" title="Error">
            {error}
          </Alert>
        ) : null}
        {note ? (
          <Alert tone="success" title="Saved">
            {note}
          </Alert>
        ) : null}

        <Card variant="accent" className="mb-8 space-y-4">
          <SectionHeader
            eyebrow="Brand preview"
            title="What sponsors see"
            description={`Your host card on ${SPONSORSHIP_HOSTS_PATH} shows verification, pitch, open slot count, and links to your Legacy Page.`}
          />
          {settings ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-[var(--radius-md)] border border-border bg-card p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                      Accepting sponsors
                    </p>
                    <p className="mt-1 font-bold text-foreground">
                      {settings.accepting_sponsors ? "On" : "Off"}
                    </p>
                  </div>
                  {canManage ? (
                    <Button size="sm" variant="secondary" onClick={() => void toggleAccepting()}>
                      {settings.accepting_sponsors ? "Turn off" : "Turn on"}
                    </Button>
                  ) : null}
                </div>
                {canManage ? (
                  <Input
                    label="Contact email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="brands@yourdomain.com"
                  />
                ) : contactEmail ? (
                  <p className="text-sm text-muted-foreground">
                    Contact: {contactEmail}
                  </p>
                ) : null}
              </div>
              <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-card p-4">
                {canManage ? (
                  <>
                    <HostSponsorshipPitchAIAssist
                      slotType={aiSlotType}
                      slotTypeLabel={
                        SPONSORSHIP_SLOT_TYPES.find((t) => t.value === aiSlotType)
                          ?.label ?? aiSlotType
                      }
                      hostNotes={aiNotes}
                      onApply={(patch) => {
                        setPitch(patch.pitch);
                        if (patch.audienceNotes) setAudienceNotes(patch.audienceNotes);
                      }}
                    />
                    <Select
                      label="Package type (for AI context)"
                      value={aiSlotType}
                      onChange={(e) => setAiSlotType(e.target.value)}
                      hint="Which slot type you are pitching — not sent to sponsors automatically."
                    >
                      {SPONSORSHIP_SLOT_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </Select>
                    <Textarea
                      label="Notes for AI (optional)"
                      value={aiNotes}
                      onChange={(e) => setAiNotes(e.target.value)}
                      hint="Angle, brand fit, or deliverables — not private inquiry content."
                      className="min-h-[72px]"
                    />
                    <Textarea
                      label="Pitch"
                      value={pitch}
                      onChange={(e) => setPitch(e.target.value)}
                      placeholder="Who comes to your nights, and why brands fit."
                    />
                    <Textarea
                      label="Audience notes"
                      value={audienceNotes}
                      onChange={(e) => setAudienceNotes(e.target.value)}
                      placeholder="City, vibe, typical turnout…"
                    />
                    <Button
                      size="sm"
                      disabled={savingSettings}
                      onClick={() => void savePitchSettings()}
                    >
                      {savingSettings ? "Saving…" : "Save pitch"}
                    </Button>
                  </>
                ) : (
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <p className="font-semibold text-foreground">Pitch</p>
                    <p className="whitespace-pre-wrap">{pitch || "—"}</p>
                    <p className="font-semibold text-foreground">Audience notes</p>
                    <p className="whitespace-pre-wrap">{audienceNotes || "—"}</p>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </Card>

        <section className="mb-10 space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <SectionHeader
              eyebrow="Packages"
              title="Your sponsorship slots"
              description="Create, edit, publish, or delete packages. Deleted slots stay under Disabled so you can restore them."
              className="pb-0"
            />
            {canManage ? (
              <Link href="/host/sponsorships/new">
                <Button size="sm">New slot</Button>
              </Link>
            ) : null}
          </div>

          {slots.length > 0 ? (
            <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
              <div
                role="tablist"
                aria-label="Sponsorship slot filters"
                className="flex min-w-0 flex-1 gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
              >
                {SPONSORSHIP_SLOT_FILTERS.map((tab) => {
                  const selected = slotFilter === tab.value;
                  return (
                    <button
                      key={tab.value}
                      type="button"
                      role="tab"
                      aria-selected={selected}
                      onClick={() => setSlotFilter(tab.value)}
                      className={cn(
                        "inline-flex shrink-0 items-center gap-1.5 rounded-[calc(var(--radius-md)-2px)] px-3 py-2 text-sm font-semibold transition-colors",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                        selected
                          ? "bg-muted text-foreground ring-1 ring-border"
                          : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
                      )}
                    >
                      {tab.label}
                      <span
                        className={cn(
                          "rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums",
                          selected
                            ? "bg-surface-elevated text-foreground"
                            : "bg-muted text-muted-foreground",
                        )}
                      >
                        {slotCounts[tab.value]}
                      </span>
                    </button>
                  );
                })}
              </div>
              <p className="shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
                {visibleSlots.length} of {slots.length}
              </p>
            </div>
          ) : null}

          {slots.length === 0 ? (
            <EmptyState
              title="No slots yet"
              description="Create a logo, booth, Vault, or Memory package so brands know exactly what they’re buying."
              action={
                canManage ? (
                  <Link href="/host/sponsorships/new">
                    <Button>Create your first slot</Button>
                  </Link>
                ) : undefined
              }
            />
          ) : visibleSlots.length === 0 ? (
            <EmptyState
              title={`No ${slotFilter} slots`}
              description="Try another filter or create a new package."
              action={
                canManage ? (
                  <Link href="/host/sponsorships/new">
                    <Button size="sm">New slot</Button>
                  </Link>
                ) : undefined
              }
            />
          ) : (
            <div className="space-y-4">
              {visibleSlots.map((slot) => (
                <SponsorSlotCard
                  key={slot.id}
                  slot={slot}
                  showModeration
                  actions={slotActions(slot)}
                />
              ))}
            </div>
          )}
        </section>

        <section className="mb-10 space-y-4">
          <SectionHeader
            eyebrow="Pipeline"
            title="Inquiries"
            description="Review brand briefs. Accepting creates a path toward placements — nothing auto-approves."
          />
          {inquiries.length === 0 ? (
            <EmptyState
              title="No inquiries yet"
              description="Once slots are published, brand inquiries will land here for review."
            />
          ) : (
            <div className="space-y-3">
              {inquiries.map((iq) => (
                <Card key={iq.id} className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-lg font-bold text-foreground">{iq.company_name}</h3>
                    <StatusBadge status={iq.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {iq.slot_title} · {iq.contact_name} · {iq.contact_email}
                    {iq.proposed_budget != null && iq.proposed_budget !== ""
                      ? ` · Budget ${iq.proposed_budget}`
                      : ""}
                  </p>
                  <p className="whitespace-pre-wrap text-sm text-muted-foreground">{iq.message}</p>
                  {canManage ? (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => void setInquiryStatus(iq.id, "reviewing")}
                      >
                        Mark reviewing
                      </Button>
                      <Button size="sm" onClick={() => void setInquiryStatus(iq.id, "accepted")}>
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => void setInquiryStatus(iq.id, "declined")}
                      >
                        Decline
                      </Button>
                    </div>
                  ) : null}
                </Card>
              ))}
            </div>
          )}
        </section>

        <section className="mb-10 space-y-4">
          <SectionHeader
            eyebrow="Performance"
            title="Placements & analytics"
            description="Confirmed placements can track impressions and clicks for brand reporting."
          />
          {placements.length === 0 ? (
            <EmptyState
              title="No placements yet"
              description="After accepting an inquiry, create a placement so brands can see delivery and impact."
            />
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {placements.map((p) => (
                <Card key={p.id} className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-bold text-foreground">{p.company_name}</p>
                    <StatusBadge status={p.status} />
                  </div>
                  <p className="text-sm text-muted-foreground">{p.slot_title}</p>
                  {p.analytics ? (
                    <div className="grid grid-cols-2 gap-2 rounded-[var(--radius-md)] bg-muted px-3 py-3 text-sm">
                      <div>
                        <p className="font-extrabold text-foreground">
                          {p.analytics.impressions}
                        </p>
                        <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                          Impressions
                        </p>
                      </div>
                      <div>
                        <p className="font-extrabold text-foreground">{p.analytics.clicks}</p>
                        <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                          Clicks
                        </p>
                      </div>
                    </div>
                  ) : null}
                </Card>
              ))}
            </div>
          )}
        </section>

        <SponsorHowItWorks
          title="How brands find you on Pàdéyá"
          description="Keep accepting sponsors on, publish clear packages, and respond to inquiries quickly."
          steps={[
            {
              title: "Turn on accepting",
              body: "Appear in the verified host marketplace when sponsorships are open.",
            },
            {
              title: "Publish slots",
              body: "Define placement type, price, and deliverables brands can inquire against.",
            },
            {
              title: "Review inquiries",
              body: "Accept or decline with a clear commercial process — no auto-approval.",
            },
            {
              title: "Deliver & track",
              body: "Placements can surface impressions and clicks for brand accountability.",
            },
          ]}
        />
      </DashboardShell>
    </RequireHost>
  );
}
