"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ParticipantAvatar } from "@/components/messaging/ParticipantAvatar";
import { Badge, Button, Modal, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  trackFanConnectSuggestionClicked,
  trackFanConnectSuggestionImpression,
} from "@/lib/analytics";
import {
  acceptConnectRequest,
  createConnectRequest,
  declineConnectRequest,
} from "@/lib/fan-connect-api";
import { DeclineRequestModal } from "@/components/fan-connect/DeclineRequestModal";
import type {
  FanConnectSuggestionBadge,
  FanConnectSuggestionReason,
  SharedContext,
} from "@/lib/types/fan-connect";

export type FanConnectCta =
  | "connect"
  | "request_sent"
  | "accept"
  | "decline"
  | "message"
  | "decline_cooldown"
  | "view_passport";

function declineCooldownCtaLabel(until: string | null | undefined): string {
  if (!until) return "Request again later";
  const ms = Date.parse(until);
  if (!Number.isFinite(ms)) return "Request again later";
  const days = Math.max(0, Math.ceil((ms - Date.now()) / 86_400_000));
  if (days <= 0) return "Request again soon";
  return `Request again available in ${days} day${days === 1 ? "" : "s"}`;
}

export type FanConnectCardProps = {
  userId?: string | null;
  displayName: string;
  username: string;
  avatarUrl?: string | null;
  tagline?: string | null;
  publicCity?: string | null;
  badges?: FanConnectSuggestionBadge[];
  matchLabel?: string | null;
  reasons?: FanConnectSuggestionReason[];
  distanceLabel?: string | null;
  mutualConnectionCount?: number | null;
  sharedContext?: SharedContext | null;
  /** Primary CTA mode for this card */
  cta: Exclude<FanConnectCta, "decline" | "view_passport">;
  connectionId?: string | null;
  threadId?: string | null;
  cooldownUntil?: string | null;
  viewerDeclinedTarget?: boolean | null;
  contextEventId?: string | null;
  scoreBand?: string | null;
  listContext?: string;
  trackSuggestionAnalytics?: boolean;
  onChanged?: () => void;
  onDismiss?: () => void;
  onMoreLikeThis?: () => void;
};

export function FanConnectCard({
  displayName,
  username,
  avatarUrl,
  tagline,
  publicCity,
  badges = [],
  matchLabel,
  reasons = [],
  distanceLabel,
  mutualConnectionCount,
  cta,
  connectionId,
  threadId,
  cooldownUntil,
  viewerDeclinedTarget,
  contextEventId,
  scoreBand,
  listContext = "fan_connect_suggestions",
  trackSuggestionAnalytics = false,
  onChanged,
  onDismiss,
  onMoreLikeThis,
}: FanConnectCardProps) {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [declineOpen, setDeclineOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const cardRef = useRef<HTMLElement | null>(null);
  const impressionFired = useRef(false);

  const passportHref = `/f/${encodeURIComponent(username)}`;
  const reasonLabels = reasons.map((r) => r.label).filter(Boolean).slice(0, 3);
  const mutualLabel =
    mutualConnectionCount && mutualConnectionCount > 0
      ? mutualConnectionCount > 1
        ? `Connected through ${mutualConnectionCount} mutual fans`
        : "Connected through someone you know"
      : null;

  useEffect(() => {
    if (!trackSuggestionAnalytics || impressionFired.current) return;
    const el = cardRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const io = new IntersectionObserver(
      (entries) => {
        const hit = entries.some((e) => e.isIntersecting && e.intersectionRatio >= 0.5);
        if (!hit) {
          if (timer) clearTimeout(timer);
          timer = null;
          return;
        }
        if (timer) return;
        timer = setTimeout(() => {
          if (impressionFired.current) return;
          impressionFired.current = true;
          trackFanConnectSuggestionImpression({
            username,
            listContext,
            scoreBand,
            ctaState: cta,
          });
        }, 500);
      },
      { threshold: [0.5] },
    );
    io.observe(el);
    return () => {
      if (timer) clearTimeout(timer);
      io.disconnect();
    };
  }, [trackSuggestionAnalytics, username, listContext, scoreBand, cta]);

  function trackClick(clickTarget: string) {
    if (!trackSuggestionAnalytics) return;
    trackFanConnectSuggestionClicked({
      username,
      listContext,
      clickTarget,
      scoreBand,
    });
  }

  function finish(okTitle: string) {
    toast.push({ tone: "success", title: okTitle });
    onChanged?.();
  }

  return (
    <>
      <article
        ref={cardRef}
        className="flex h-full flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated dark:shadow-[var(--shadow)]"
      >
        <div className="flex items-start gap-3">
          <ParticipantAvatar
            name={displayName}
            avatarUrl={avatarUrl}
            size="lg"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate font-extrabold text-heading">{displayName}</p>
            <Link
              href={passportHref}
              className="text-sm text-muted-foreground hover:text-primary"
              onClick={() => trackClick("view_passport")}
            >
              @{username}
            </Link>
            {matchLabel ? (
              <p className="mt-1 text-xs font-semibold text-primary">
                {matchLabel}
              </p>
            ) : null}
            {publicCity ? (
              <p className="mt-0.5 text-xs text-muted-foreground">{publicCity}</p>
            ) : null}
            {distanceLabel ? (
              <p className="mt-0.5 text-xs font-medium text-muted-foreground">
                {distanceLabel}
              </p>
            ) : null}
          </div>
        </div>

        {tagline ? (
          <p className="line-clamp-2 text-sm text-foreground/75">{tagline}</p>
        ) : null}

        {badges.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {badges.slice(0, 3).map((b) => (
              <Badge key={b.slug} tone="outline" size="sm">
                {b.name}
              </Badge>
            ))}
          </div>
        ) : null}

        <ul className="space-y-0.5">
          {mutualLabel &&
          !reasonLabels.some((l) => l.toLowerCase().includes("mutual")) ? (
            <li className="text-xs text-muted-foreground">{mutualLabel}</li>
          ) : null}
          {reasonLabels.map((label) => (
            <li key={label} className="text-xs text-muted-foreground">
              {label}
            </li>
          ))}
        </ul>

        <div className="mt-auto flex flex-wrap gap-2 pt-1">
          {cta === "connect" ? (
            <>
              <Button
                size="sm"
                disabled={busy}
                onClick={() => {
                  trackClick("connect");
                  setError(null);
                  setOpen(true);
                }}
              >
                {viewerDeclinedTarget ? "Send connect request" : "Connect"}
              </Button>
              {viewerDeclinedTarget ? (
                <p className="w-full text-xs text-muted-foreground">
                  You declined their earlier request. You can still connect if
                  you want.
                </p>
              ) : null}
            </>
          ) : null}

          {cta === "decline_cooldown" ? (
            <Button size="sm" variant="secondary" disabled>
              {declineCooldownCtaLabel(cooldownUntil)}
            </Button>
          ) : null}

          {cta === "request_sent" ? (
            <Link href="/connect/requests">
              <Button size="sm" variant="secondary">
                Request sent
              </Button>
            </Link>
          ) : null}

          {cta === "accept" && connectionId ? (
            <>
              <Button
                size="sm"
                disabled={busy}
                onClick={() => {
                  setBusy(true);
                  void acceptConnectRequest(connectionId)
                    .then((row) => {
                      finish("Connected");
                      if (row.thread_id) {
                        router.push(`/dashboard/messages/${row.thread_id}`);
                      }
                    })
                    .catch((err) =>
                      setError(
                        err instanceof ApiError
                          ? err.detail
                          : "Could not accept.",
                      ),
                    )
                    .finally(() => setBusy(false));
                }}
              >
                Accept
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={busy}
                onClick={() => {
                  setError(null);
                  setDeclineOpen(true);
                }}
              >
                Decline
              </Button>
            </>
          ) : null}

          {cta === "message" && threadId ? (
            <Link href={`/dashboard/messages/${threadId}`}>
              <Button size="sm">Message</Button>
            </Link>
          ) : null}

          <Link href={passportHref}>
            <Button size="sm" variant="secondary">
              View Passport
            </Button>
          </Link>

          {onMoreLikeThis ? (
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                trackClick("more_like_this");
                onMoreLikeThis();
              }}
            >
              More like this
            </Button>
          ) : null}

          {onDismiss ? (
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                trackClick("dismiss");
                onDismiss();
              }}
            >
              Not interested
            </Button>
          ) : null}
        </div>

        {error ? (
          <p className="text-xs font-semibold text-danger">{error}</p>
        ) : null}
      </article>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Fan Connect"
        description="Shared event energy — stay on Pàdéyá, no phone numbers."
      >
        <div className="space-y-3">
          {reasonLabels.length > 0 ? (
            <ul className="space-y-1">
              {reasonLabels.map((label) => (
                <li key={label} className="text-sm text-muted-foreground">
                  {label}
                </li>
              ))}
            </ul>
          ) : null}
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value.slice(0, 280))}
            rows={3}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Optional short intro (no contact details)"
          />
          {error ? (
            <p className="text-sm font-semibold text-danger">{error}</p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busy}
              onClick={() => {
                setBusy(true);
                setError(null);
                void createConnectRequest({
                  username,
                  message: message.trim() || undefined,
                  context_event_id: contextEventId || undefined,
                })
                  .then(() => {
                    setOpen(false);
                    finish("Request sent");
                    router.push("/connect/requests");
                  })
                  .catch((err) =>
                    setError(
                      err instanceof ApiError
                        ? typeof err.detail === "string"
                          ? err.detail
                          : "Could not send request"
                        : "Could not send request",
                    ),
                  )
                  .finally(() => setBusy(false));
              }}
            >
              Send request
            </Button>
          </div>
        </div>
      </Modal>

      {connectionId ? (
        <DeclineRequestModal
          open={declineOpen}
          onClose={() => setDeclineOpen(false)}
          busy={busy}
          onConfirm={async (cooldownDays) => {
            setBusy(true);
            try {
              await declineConnectRequest(connectionId, {
                cooldown_days: cooldownDays,
              });
              setDeclineOpen(false);
              finish("Declined");
            } catch (err) {
              setError(
                err instanceof ApiError ? err.detail : "Could not decline.",
              );
            } finally {
              setBusy(false);
            }
          }}
        />
      ) : null}
    </>
  );
}
