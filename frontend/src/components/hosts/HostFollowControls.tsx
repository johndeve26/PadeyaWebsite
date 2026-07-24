"use client";

import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Modal } from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  fetchMyFollowing,
  followHost,
  unfollowHost,
  updateMarketingOptIn,
} from "@/lib/crm-api";
import { isPlaceholderDiscoverHostId } from "@/lib/hosts-demo";

function BellIcon({ active, className }: { active?: boolean; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={cn("h-5 w-5", className)}
    >
      <path
        d="M12 3.5c-2.6 0-4.7 2.1-4.7 4.7v2.1c0 .9-.3 1.7-.9 2.4l-.8.9c-.7.8-.2 2.1.9 2.1h11c1.1 0 1.6-1.3.9-2.1l-.8-.9c-.6-.7-.9-1.5-.9-2.4V8.2c0-2.6-2.1-4.7-4.7-4.7Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
        fill={active ? "currentColor" : "none"}
        fillOpacity={active ? 0.18 : 0}
      />
      <path
        d="M10 18.5a2 2 0 0 0 4 0"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

type HostFollowControlsProps = {
  hostId: string;
  /** Legacy username / slug — used to follow when hostId is a demo placeholder. */
  hostSlug?: string;
  hostDisplayName: string;
  loginNextPath: string;
  /** Optimistic initial follow state before /me/following loads. */
  initialFollowing?: boolean;
  className?: string;
  buttonClassName?: string;
  size?: "md" | "lg";
  /** Fired when follow/unfollow changes (+1 / -1) for local follower counts. */
  onFollowDelta?: (delta: number) => void;
  onError?: (message: string) => void;
  /** Analytics / side effects before the follow API call. */
  onBeforeFollowToggle?: () => void;
  /** When false, skip the post-follow modal (e.g. dense cards). */
  promptAfterFollow?: boolean;
  /** Equal-width follow row on marketplace cards (Follow spans full row until following). */
  layout?: "default" | "card-row";
};

/**
 * Follow + email notify (bell). Privacy default: follow does not opt into email;
 * after Follow we invite the fan to turn notifications on explicitly.
 */
export function HostFollowControls({
  hostId,
  hostSlug,
  hostDisplayName,
  loginNextPath,
  initialFollowing = false,
  className,
  buttonClassName,
  size = "lg",
  onFollowDelta,
  onError,
  onBeforeFollowToggle,
  promptAfterFollow = true,
  layout = "default",
}: HostFollowControlsProps) {
  const { user } = useAuth();
  const [effectiveHostId, setEffectiveHostId] = useState(hostId);
  const { affiliated: isOwnHost } = useHostAffiliation({
    hostId: effectiveHostId,
    hostSlug,
  });
  const [following, setFollowing] = useState(initialFollowing);
  const [emailNotify, setEmailNotify] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notifyBusy, setNotifyBusy] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  /** Bumps on follow/unfollow so in-flight /me/following cannot revert UI. */
  const followMutationGen = useRef(0);

  useEffect(() => {
    setEffectiveHostId(hostId);
  }, [hostId]);

  useEffect(() => {
    if (!user || isOwnHost) {
      setFollowing(false);
      setEmailNotify(false);
      return;
    }
    let active = true;
    const syncGen = followMutationGen.current;
    const slugNorm = hostSlug?.replace(/^@/, "").trim().toLowerCase() ?? "";
    void fetchMyFollowing()
      .then((rows) => {
        if (!active || followMutationGen.current !== syncGen) return;
        const row = rows.find(
          (r) =>
            r.host_id === hostId ||
            (slugNorm.length > 0 && r.username.toLowerCase() === slugNorm),
        );
        if (row) {
          setEffectiveHostId(row.host_id);
          setFollowing(true);
          setEmailNotify(Boolean(row.marketing_opt_in));
        } else {
          setFollowing(initialFollowing);
          setEmailNotify(false);
        }
      })
      .catch(() => {
        if (!active || followMutationGen.current !== syncGen) return;
        setFollowing(initialFollowing);
        setEmailNotify(false);
      });
    return () => {
      active = false;
    };
  }, [user, hostId, hostSlug, isOwnHost, initialFollowing]);

  if (isOwnHost) {
    return null;
  }

  const isFollowing = Boolean(user && following);
  const notifyOn = Boolean(user && emailNotify);

  async function onFollowToggle() {
    onBeforeFollowToggle?.();
    if (!user) {
      window.location.href = `/login?next=${encodeURIComponent(loginNextPath)}`;
      return;
    }
    setBusy(true);
    followMutationGen.current += 1;
    try {
      if (isFollowing) {
        await unfollowHost(effectiveHostId);
        followMutationGen.current += 1;
        setFollowing(false);
        setEmailNotify(false);
        setPromptOpen(false);
        onFollowDelta?.(-1);
      } else {
        const slug = hostSlug?.replace(/^@/, "").trim();
        const followPayload =
          slug
            ? { host_slug: slug }
            : isPlaceholderDiscoverHostId(hostId) ||
                isPlaceholderDiscoverHostId(effectiveHostId)
              ? null
              : { host_id: effectiveHostId };
        if (!followPayload) {
          onError?.("Could not resolve this host — refresh and try again.");
          return;
        }
        const row = await followHost(followPayload);
        followMutationGen.current += 1;
        setEffectiveHostId(row.host_id);
        setFollowing(true);
        setEmailNotify(Boolean(row.marketing_opt_in));
        onFollowDelta?.(1);
        if (promptAfterFollow && !row.marketing_opt_in) {
          setPromptOpen(true);
        }
      }
    } catch (err) {
      onError?.(err instanceof ApiError ? err.detail : "Follow failed");
    } finally {
      setBusy(false);
    }
  }

  async function setNotify(enabled: boolean) {
    if (!user || !isFollowing) return;
    setNotifyBusy(true);
    try {
      const row = await updateMarketingOptIn(effectiveHostId, enabled);
      setEmailNotify(row.marketing_opt_in);
      setPromptOpen(false);
    } catch (err) {
      onError?.(
        err instanceof ApiError ? err.detail : "Could not update email notifications",
      );
    } finally {
      setNotifyBusy(false);
    }
  }

  const cardRow = layout === "card-row";

  return (
    <>
      <div
        className={cn(
          cardRow
            ? "grid w-full grid-cols-2 gap-2"
            : "flex flex-wrap items-center justify-center gap-2.5",
          className,
        )}
      >
        <Button
          type="button"
          size={size}
          variant={isFollowing ? (size === "lg" ? "outline-dark" : "secondary") : "primary"}
          disabled={busy}
          onClick={() => void onFollowToggle()}
          className={cn(
            "padeya-btn-micro",
            cardRow && !isFollowing && "col-span-2",
            cardRow && isFollowing && "col-span-1 w-full",
            !cardRow && (size === "lg" ? "min-w-[160px] px-8" : "w-full sm:flex-1"),
            buttonClassName,
          )}
        >
          {busy ? "…" : isFollowing ? "Following" : "Follow"}
        </Button>

        {isFollowing ? (
          <Button
            type="button"
            size={size}
            variant={notifyOn ? "primary" : size === "lg" ? "outline-dark" : "secondary"}
            disabled={notifyBusy}
            onClick={() => void setNotify(!notifyOn)}
            className={cn(
              "padeya-btn-micro inline-flex items-center justify-center gap-2",
              cardRow ? "col-span-1 w-full" : size === "lg" ? "px-4" : "w-full sm:flex-1",
            )}
            aria-pressed={notifyOn}
            aria-label={
              notifyOn
                ? "Email notifications on — click to turn off"
                : "Turn on email notifications for this host"
            }
            title={
              notifyOn
                ? "Email updates on — click to mute"
                : "Get email updates when they announce events"
            }
          >
            <BellIcon active={notifyOn} />
            <span className="text-sm font-bold">
              {notifyOn ? "Notified" : "Notify me"}
            </span>
          </Button>
        ) : null}
      </div>

      <Modal
        open={promptOpen}
        onClose={() => setPromptOpen(false)}
        title="Get updates by email?"
        description={`You’re following ${hostDisplayName}. Turn on the bell to hear about new events and drops — only from this host, and you can mute anytime.`}
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={notifyBusy}
              onClick={() => setPromptOpen(false)}
            >
              Not now
            </Button>
            <Button
              size="sm"
              variant="primary"
              disabled={notifyBusy}
              onClick={() => void setNotify(true)}
              className="inline-flex items-center gap-2"
            >
              <BellIcon active />
              {notifyBusy ? "Saving…" : "Turn on email updates"}
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-sm leading-relaxed text-muted-foreground">
          <div className="flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-muted/40 px-3.5 py-3">
            <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-accent">
              <BellIcon active />
            </span>
            <div className="min-w-0 space-y-1">
              <p className="font-bold text-foreground">What you’ll get</p>
              <p>
                Email when {hostDisplayName} shares upcoming events or important
                Legacy updates on Pàdéyá.
              </p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Following alone does not subscribe you. Notifications stay off until you
            choose Notify me.
          </p>
        </div>
      </Modal>
    </>
  );
}
