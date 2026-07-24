"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AmbassadorShareCard } from "@/components/ambassadors/AmbassadorShareCard";
import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Modal } from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import { ApiError } from "@/lib/api";
import {
  buildAmbassadorEventLink,
  formatAmbassadorCodeDisplay,
} from "@/lib/ambassador-referral";
import {
  fetchMyEventAmbassador,
  fetchOpenAmbassadorProgram,
  joinOpenEventAmbassador,
} from "@/lib/promos-api";
import type { EventItem } from "@/lib/types/events";
import type {
  Ambassador,
  OpenAmbassadorCampaignOption,
  OpenAmbassadorProgram,
} from "@/lib/types/promos";

/**
 * Compact Event Ambassadors CTA for eligible event pages.
 * Details (terms, link/code) live in a modal to avoid clutter.
 */
export function PromoteEventAmbassadors({
  event,
  previewMode = false,
}: {
  event: EventItem;
  previewMode?: boolean;
}) {
  const { user, loading: authLoading } = useAuth();
  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: event.host_id,
    hostSlug: event.host_slug,
  });
  const [open, setOpen] = useState(false);
  const [program, setProgram] = useState<OpenAmbassadorProgram | null>(null);
  const [campaignType, setCampaignType] = useState("event_tickets");
  const [enrollment, setEnrollment] = useState<Ambassador | null>(null);
  const [loadingEnrollment, setLoadingEnrollment] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<"link" | "code" | null>(null);
  const [acceptTerms, setAcceptTerms] = useState(false);

  const eligible = Boolean(event.open_ambassadors_enabled);
  const options: OpenAmbassadorCampaignOption[] = program?.campaigns?.length
    ? program.campaigns
    : program?.enabled
      ? [
          {
            id: program.campaign_id || "legacy",
            campaign_type: program.campaign_type || "event_tickets",
            campaign_type_label:
              program.campaign_type === "event_merch"
                ? "Event Merch Ambassador"
                : "Event Ambassador",
            commission_percent: program.commission_percent,
            merch_included: Boolean(program.merch_included),
            is_live: true,
          },
        ]
      : [];
  const cardCommission =
    program?.commission_value ??
    program?.commission_percent ??
    event.open_ambassador_commission_percent;
  const cardCommissionType = program?.commission_type || "percentage";

  useEffect(() => {
    if (previewMode || !eligible) return;
    if (typeof window === "undefined") return;
    if (window.location.hash === "#promote-ambassadors") {
      queueMicrotask(() => setOpen(true));
    }
  }, [eligible, previewMode]);

  // Prefetch program so the closed card can show commission/reward summary.
  useEffect(() => {
    if (previewMode || !eligible) return;
    let active = true;
    void (async () => {
      try {
        const prog = await fetchOpenAmbassadorProgram(event.id);
        if (!active) return;
        setProgram(prog);
        const first = prog.campaigns?.[0]?.campaign_type || "event_tickets";
        setCampaignType(first);
      } catch {
        if (active) setProgram(null);
      }
    })();
    return () => {
      active = false;
    };
  }, [event.id, eligible, previewMode]);

  // Prefetch enrollment so the closed card can show "View my link".
  useEffect(() => {
    if (previewMode || !eligible || !user || !campaignType) {
      if (!user) {
        queueMicrotask(() => setEnrollment(null));
      }
      return;
    }
    let active = true;
    queueMicrotask(() => setLoadingEnrollment(true));
    void (async () => {
      try {
        const row = await fetchMyEventAmbassador(event.id, campaignType);
        if (active) setEnrollment(row.status === "active" ? row : null);
      } catch (err) {
        if (active) {
          setEnrollment(null);
          if (open && !(err instanceof ApiError && err.status === 404)) {
            setError(
              err instanceof ApiError
                ? err.detail
                : "Could not load ambassador status",
            );
          }
        }
      } finally {
        if (active) setLoadingEnrollment(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [event.id, eligible, previewMode, user, campaignType, open]);

  if (previewMode || !eligible || isOwnHost) return null;

  const returnPath = `/events/${event.slug}#promote-ambassadors`;
  const loginHref = `/login?next=${encodeURIComponent(returnPath)}`;
  const registerHref = `/register?next=${encodeURIComponent(returnPath)}`;
  const selected = options.find((o) => o.campaign_type === campaignType);
  const earnCopy =
    campaignType === "event_merch"
      ? "Share this event’s merch and earn when people buy through your link."
      : "Share this event and earn when people buy tickets through your link.";

  async function onJoin() {
    if (!acceptTerms) {
      setError("Accept the Ambassador terms to continue");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const row = await joinOpenEventAmbassador(event.id, {
        accept_terms: true,
        campaign_type: campaignType,
      });
      setEnrollment(row);
      setAcceptTerms(false);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not join Ambassadors",
      );
    } finally {
      setBusy(false);
    }
  }

  async function copy(kind: "link" | "code", value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      setError("Could not copy — copy the Ambassador link manually");
    }
  }

  function closeModal() {
    setOpen(false);
    setError(null);
    setAcceptTerms(false);
    setCopied(null);
  }

  return (
    <>
      <div
        id="promote-ambassadors"
        className="scroll-mt-24 rounded-[var(--radius-xl)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)] sm:p-5"
      >
        <h3 className="text-base font-extrabold text-heading">
          Promote this event
        </h3>
        <p className="mt-1.5 text-sm leading-snug text-muted-foreground">
          Join Ambassadors, share your link, and earn on verified sales.
        </p>
        {cardCommission != null ? (
          <p className="mt-2 text-sm font-semibold text-heading">
            {cardCommissionType === "flat"
              ? `₦${cardCommission} flat per sale`
              : cardCommissionType === "reward_only"
                ? "Reward-only campaign"
                : `${cardCommission}% commission`}
          </p>
        ) : null}
        <Button
          className="mt-3 w-full"
          size="sm"
          onClick={() => {
            setError(null);
            setOpen(true);
          }}
        >
          {enrollment ? "View my link" : "Join & promote"}
        </Button>
      </div>

      <Modal
        open={open}
        onClose={closeModal}
        title="Promote this event"
        description={earnCopy}
        className="sm:max-w-md"
        footer={
          enrollment ? (
            <>
              <Link href="/dashboard/ambassador/links" onClick={closeModal}>
                <Button variant="secondary" size="sm">
                  My links
                </Button>
              </Link>
              <Button size="sm" onClick={closeModal}>
                Done
              </Button>
            </>
          ) : undefined
        }
      >
        {error ? (
          <p className="mb-3 text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}

        {options.length > 1 ? (
          <div className="mb-4 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Campaign
            </p>
            <div className="flex flex-col gap-2">
              {options.map((opt) => (
                <label
                  key={opt.id}
                  className="flex cursor-pointer items-start gap-2 rounded-[var(--radius-md)] border border-border px-3 py-2 text-sm"
                >
                  <input
                    type="radio"
                    name="campaign_type"
                    className="mt-1"
                    checked={campaignType === opt.campaign_type}
                    onChange={() => {
                      setCampaignType(opt.campaign_type);
                      setAcceptTerms(false);
                      setError(null);
                    }}
                  />
                  <span>
                    <span className="font-semibold text-foreground">
                      {opt.campaign_type_label}
                    </span>
                    <span className="mt-0.5 block text-muted-foreground">
                      {opt.commission_percent}% commission ·{" "}
                      {opt.campaign_type === "event_merch"
                        ? "merch orders"
                        : "ticket sales"}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        ) : selected ? (
          <p className="mb-3 text-sm text-muted-foreground">
            {selected.campaign_type_label} · {selected.commission_percent}%
            commission
          </p>
        ) : null}

        {authLoading || loadingEnrollment ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : !user ? (
          <div className="space-y-4">
            <p className="text-sm text-body">
              Log in or create a Pàdéyá account to get your Ambassador link.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Link href={loginHref} className="flex-1">
                <Button className="w-full" size="sm">
                  Log in
                </Button>
              </Link>
              <Link href={registerHref} className="flex-1">
                <Button className="w-full" size="sm" variant="secondary">
                  Register
                </Button>
              </Link>
            </div>
          </div>
        ) : enrollment ? (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Ambassador code
              </p>
              <p className="mt-1 font-mono text-lg font-bold tracking-wide text-foreground">
                {enrollment.referral_code_display ||
                  formatAmbassadorCodeDisplay(enrollment.referral_code)}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Ambassador link
              </p>
              <p className="mt-1 break-all text-sm text-body">
                {buildAmbassadorEventLink(event.slug, enrollment.referral_code, {
                  merch: campaignType === "event_merch",
                })}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  void copy(
                    "link",
                    buildAmbassadorEventLink(
                      event.slug,
                      enrollment.referral_code,
                      { merch: campaignType === "event_merch" },
                    ),
                  )
                }
              >
                {copied === "link" ? "Copied link" : "Copy link"}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  void copy(
                    "code",
                    enrollment.referral_code_display ||
                      formatAmbassadorCodeDisplay(enrollment.referral_code),
                  )
                }
              >
                {copied === "code" ? "Copied code" : "Copy code"}
              </Button>
            </div>
            <AmbassadorShareCard
              eventTitle={event.title}
              code={enrollment.referral_code}
              link={buildAmbassadorEventLink(
                event.slug,
                enrollment.referral_code,
                { merch: campaignType === "event_merch" },
              )}
              campaignLabel={selected?.campaign_type_label}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-body">
              Accept the Ambassador terms to create your promoter profile for
              this campaign and get a unique link. This does not grant host team
              or scanner access.
            </p>
            <label className="flex items-start gap-2 text-sm text-body">
              <input
                type="checkbox"
                className="mt-1"
                checked={acceptTerms}
                onChange={(e) => setAcceptTerms(e.target.checked)}
              />
              <span>I accept the Pàdéyá Ambassadors terms.</span>
            </label>
            <Button
              className="w-full"
              size="sm"
              disabled={busy || !acceptTerms}
              onClick={() => void onJoin()}
            >
              {busy ? "Creating link…" : "Get my Ambassador link"}
            </Button>
          </div>
        )}
      </Modal>
    </>
  );
}
