"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Modal, useToast } from "@/components/ui";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { trackHostMessageFanClicked } from "@/lib/analytics";
import { ApiError } from "@/lib/api";
import { userHasRole } from "@/lib/auth/permissions";
import {
  cancelConnectRequest,
  createConnectRequest,
  fetchCanConnect,
  removeConnection,
} from "@/lib/fan-connect-api";
import type { CanConnect } from "@/lib/types/fan-connect";
import { formatSelfMessageError } from "@/lib/messaging-errors";
import {
  createHostThread,
  hostCanMessageFanUsername,
} from "@/lib/messaging-api";
import { isOwnFanPassport } from "@/lib/own-fan-ctas";
import { USER_RESTRICTION_ACTION_MESSAGE } from "@/lib/user-restrictions";

function denialCopy(
  denials: string[],
  message?: string | null,
  state?: CanConnect | null,
): string {
  if (message?.trim()) return message.trim();
  if (denials.includes("self")) {
    return "You can’t connect with yourself.";
  }
  if (state?.viewer_declined_target && !denials.includes("decline_cooldown")) {
    return "You declined their earlier request. You can still connect if you want.";
  }
  if (denials.includes("actor_connect_off")) {
    return "Turn on Fan Connect in your settings to request a connection.";
  }
  if (denials.includes("target_connect_off") || denials.includes("target_requests_off")) {
    return "This fan isn’t accepting Connect requests right now.";
  }
  if (
    denials.includes("no_shared_public_context") ||
    denials.includes("policy_requires_shared_event") ||
    denials.includes("policy_requires_shared_host")
  ) {
    return "No shared public events, hosts, or scenes yet.";
  }
  if (denials.includes("passport_not_public")) {
    return "Connect needs a public Fan Passport.";
  }
  if (denials.includes("blocked") || denials.includes("connection_blocked")) {
    return "Messaging isn’t available with this fan.";
  }
  if (denials.includes("decline_cooldown")) {
    if (state?.cooldown_until) {
      const d = new Date(state.cooldown_until);
      if (!Number.isNaN(d.getTime())) {
        return `Request again available on ${d.toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
          year: "numeric",
        })}.`;
      }
    }
    return "Request again available after the cooldown ends.";
  }
  if (denials.includes("request_pending")) {
    return "A Connect request is already pending.";
  }
  return "Connect isn’t available right now.";
}

function canSendConnect(state: CanConnect | null): boolean {
  if (!state) return false;
  if (state.can_send_connect_request != null) return state.can_send_connect_request;
  return state.allowed;
}

function formatConnectError(err: unknown): string {
  if (!(err instanceof ApiError)) return "Could not send request";
  const detail = typeof err.detail === "string" ? err.detail.trim() : "";
  if (!detail) return "Could not send request";
  if (
    detail === "You can’t connect with yourself." ||
    detail.toLowerCase().includes("connect with yourself")
  ) {
    return "You can’t connect with yourself.";
  }
  return detail;
}

type Props = {
  username: string;
  /** Passport owner user id — preferred own-page gate (user id, not username). */
  passportOwnerUserId?: string | null;
  /** @deprecated Prefer passportOwnerUserId; kept for call sites that already computed ownership. */
  isOwner?: boolean;
  /** Fan Connect request CTA (public passports). */
  showConnect?: boolean;
  /** Message CTA (fan thread, host DM, or connect-first). */
  showMessage?: boolean;
  size?: "sm" | "md" | "lg";
  /** Tighter layout for directory cards (shorter hints). */
  compact?: boolean;
  /** Hero (dark) vs directory cards (light). */
  surface?: "dark" | "light";
};

export function ConnectButton({
  username,
  passportOwnerUserId = null,
  isOwner = false,
  showConnect = true,
  showMessage = true,
  size = "lg",
  compact = false,
  surface = "dark",
}: Props) {
  const { user, loading: authLoading } = useAuth();
  const { has } = useUserRestrictions();
  const cannotConnect = has("cannot_use_fan_connect");
  const cannotMessage = has("cannot_message");
  const isOwnPassport =
    isOwner || isOwnFanPassport(user?.id, passportOwnerUserId);
  const router = useRouter();
  const pathname = usePathname();
  const toast = useToast();
  const isHost = Boolean(user && userHasRole(user, "host", "host_staff"));
  const [state, setState] = useState<CanConnect | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [hostAllowed, setHostAllowed] = useState<boolean | null>(null);
  const [hostOpen, setHostOpen] = useState(false);
  const [hostBody, setHostBody] = useState("");
  const [hostBusy, setHostBusy] = useState(false);
  const [hostError, setHostError] = useState<string | null>(null);

  const loginNext = `/login?next=${encodeURIComponent(pathname || `/f/${username}`)}`;
  const outlineVariant = surface === "light" ? "secondary" : "outline-dark";
  const hintClass =
    surface === "light"
      ? "max-w-[14rem] text-xs font-semibold leading-snug text-muted-foreground"
      : "max-w-[14rem] text-xs font-semibold leading-snug text-paper/70";

  function refreshCanConnect() {
    return fetchCanConnect(username)
      .then((data) => {
        setState(data);
        setLoadError(false);
        return data;
      })
      .catch(() => {
        setLoadError(true);
        return null;
      });
  }

  useEffect(() => {
    if (!user || isOwnPassport || !username) return;
    let active = true;
    void fetchCanConnect(username)
      .then((data) => {
        if (active) {
          setState(data);
          setLoadError(false);
        }
      })
      .catch(() => {
        if (active) {
          setState(null);
          setLoadError(true);
        }
      });
    return () => {
      active = false;
    };
  }, [user, username, isOwnPassport]);

  useEffect(() => {
    if (!isHost || !username || isOwnPassport) return;
    let active = true;
    void hostCanMessageFanUsername(username)
      .then((ok) => {
        if (active) setHostAllowed(ok);
      })
      .catch(() => {
        if (active) setHostAllowed(false);
      });
    return () => {
      active = false;
    };
  }, [isHost, username, isOwnPassport]);

  const effectiveHostAllowed =
    !isHost || !username || isOwnPassport ? null : hostAllowed;

  if (isOwnPassport || (!showConnect && !showMessage)) return null;

  if (authLoading) {
    return (
      <div
        className={
          compact
            ? "flex w-full gap-2 [&_button]:w-full"
            : "contents"
        }
      >
        {showConnect ? (
          <div className={compact ? "min-w-0 flex-1" : undefined}>
            <Button size={size} disabled>
              Connect
            </Button>
          </div>
        ) : null}
        {showMessage ? (
          <div className={compact ? "min-w-0 flex-1" : undefined}>
            <Button size={size} variant={outlineVariant} disabled>
              Message
            </Button>
          </div>
        ) : null}
      </div>
    );
  }

  if (!user) {
    return (
      <div
        className={
          compact
            ? "flex w-full gap-2 [&_a]:block [&_a]:w-full [&_button]:w-full"
            : "contents"
        }
      >
        {showConnect ? (
          <div className={compact ? "min-w-0 flex-1" : undefined}>
            <Link href={loginNext}>
              <Button size={size}>Connect</Button>
            </Link>
          </div>
        ) : null}
        {showMessage ? (
          <div className={compact ? "min-w-0 flex-1" : undefined}>
            <Link href={loginNext}>
              <Button size={size} variant={outlineVariant}>
                Message
              </Button>
            </Link>
          </div>
        ) : null}
      </div>
    );
  }

  const connected = state?.connection_status === "connected";
  const requestSent = state?.connection_status === "request_sent";
  const requestReceived = state?.connection_status === "request_received";
  const pending = requestSent || requestReceived;
  const loadingConnect = !state && !loadError;

  async function sendConnectRequest() {
    if (!state || !canSendConnect(state) || busy) return;
    const snapshot = state;
    setBusy(true);
    setState({
      ...snapshot,
      allowed: false,
      reasons: [...snapshot.reasons, "request_pending"],
      denials: [...snapshot.denials, "request_pending"],
      connection_status: "request_sent",
      shared_context: snapshot.shared_context,
    });
    setHint(null);
    try {
      const conn = await createConnectRequest({
        username,
      });
      setState({
        allowed: false,
        reasons: ["request_pending"],
        denials: ["request_pending"],
        shared_context: snapshot.shared_context,
        connection_status: "request_sent",
        connection_id: conn.id,
        thread_id: conn.thread_id ?? null,
      });
      toast.push({
        tone: "success",
        title: "Connect requested",
        description: "They’ll get a notification to review it.",
      });
      await refreshCanConnect();
    } catch (err) {
      await refreshCanConnect();
      const copy = formatConnectError(err);
      toast.push({
        tone: "danger",
        title: "Couldn’t send Connect request",
        description: copy,
      });
    } finally {
      setBusy(false);
    }
  }

  function onConnectClick() {
    if (!state) return;
    if (canSendConnect(state)) {
      void sendConnectRequest();
      return;
    }
    const copy = denialCopy(state.denials, state.message, state);
    setHint(copy);
    toast.push({
      tone: "warning",
      title: "Connect unavailable",
      description: copy,
      href: state.denials.includes("actor_connect_off")
        ? "/connect/settings"
        : undefined,
      actionLabel: state.denials.includes("actor_connect_off")
        ? "Open settings"
        : undefined,
    });
  }

  async function cancelPendingRequest() {
    const connectionId = state?.connection_id;
    if (!connectionId || busy) return;
    setBusy(true);
    setHint(null);
    try {
      await cancelConnectRequest(connectionId);
      toast.push({
        tone: "success",
        title: "Connect request cancelled",
        description: "You can send a new request anytime.",
      });
      await refreshCanConnect();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Couldn’t cancel request",
        description:
          err instanceof ApiError && typeof err.detail === "string"
            ? err.detail
            : "Try again from Connect → Requests.",
      });
      await refreshCanConnect();
    } finally {
      setBusy(false);
    }
  }

  async function disconnectConnection() {
    const connectionId = state?.connection_id;
    if (!connectionId || busy) return;
    setBusy(true);
    setHint(null);
    try {
      await removeConnection(connectionId);
      toast.push({
        tone: "success",
        title: "Connection removed",
        description: "You can send a new Connect request anytime.",
      });
      await refreshCanConnect();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Couldn’t remove connection",
        description:
          err instanceof ApiError && typeof err.detail === "string"
            ? err.detail
            : "Try again from Connect → Connections.",
      });
      await refreshCanConnect();
    } finally {
      setBusy(false);
    }
  }

  let connectControl: ReactNode = null;
  if (showConnect) {
    if (loadingConnect) {
      connectControl = (
        <Button size={size} disabled>
          Connect
        </Button>
      );
    } else if (connected) {
      connectControl = (
        <Button
          size={size}
          variant="secondary"
          disabled={busy || !state?.connection_id}
          onClick={() => void disconnectConnection()}
        >
          {busy ? "Removing…" : "Connection"}
        </Button>
      );
    } else if (requestSent) {
      connectControl = (
        <Button
          size={size}
          variant={outlineVariant}
          disabled={busy || !state?.connection_id}
          onClick={() => void cancelPendingRequest()}
          title="Click to cancel your pending Connect request"
        >
          {busy ? "Cancelling…" : "Connect requested"}
        </Button>
      );
    } else if (requestReceived) {
      connectControl = (
        <Link href="/connect/requests">
          <Button size={size} variant={outlineVariant}>
            Respond to request
          </Button>
        </Link>
      );
    } else if (loadError) {
      connectControl = (
        <Button
          size={size}
          variant={outlineVariant}
          onClick={() => {
            setLoadError(false);
            setState(null);
            void refreshCanConnect().then((data) => {
              if (!data) {
                toast.push({
                  tone: "danger",
                  title: "Fan Connect unavailable",
                  description: "Couldn’t check Connect status. Try again.",
                });
              }
            });
          }}
        >
          Connect
        </Button>
      );
    } else if (state && !canSendConnect(state)) {
      if (state.denials.includes("actor_connect_off")) {
        connectControl = (
          <Link href="/connect/settings">
            <Button size={size} variant={outlineVariant}>
              Turn on Fan Connect
            </Button>
          </Link>
        );
      } else {
        connectControl = (
          <Button
            size={size}
            variant={outlineVariant}
            disabled={busy || state.denials.includes("decline_cooldown")}
            onClick={onConnectClick}
            title={denialCopy(state.denials, state.message, state)}
          >
            {state.denials.includes("decline_cooldown")
              ? "On cooldown"
              : "Connect"}
          </Button>
        );
      }
    } else {
      connectControl = (
        <Button size={size} disabled={busy} onClick={onConnectClick}>
          {busy ? "Sending…" : "Connect"}
        </Button>
      );
    }
    if (cannotConnect) {
      connectControl = (
        <Button
          size={size}
          disabled
          title={USER_RESTRICTION_ACTION_MESSAGE}
        >
          Connect
        </Button>
      );
    }
  }

  function onMessageClick() {
    if (connected && state?.thread_id) {
      router.push(`/dashboard/messages/${state.thread_id}`);
      return;
    }
    if (isHost && effectiveHostAllowed === true) {
      trackHostMessageFanClicked();
      setHostOpen(true);
    }
  }

  const canMessage =
    !cannotMessage &&
    (Boolean(connected && state?.thread_id) ||
      Boolean(isHost && effectiveHostAllowed === true));
  const messageHint = cannotMessage
    ? USER_RESTRICTION_ACTION_MESSAGE
    : !canMessage
      ? pending
        ? "Connect request pending — message unlocks after they accept."
        : "Connect first to send a message."
      : null;

  const messageControl = showMessage ? (
    <div className={compact ? undefined : "flex flex-col gap-1"}>
      {cannotMessage ? (
        <Button
          size={size}
          variant={outlineVariant}
          disabled
          title={USER_RESTRICTION_ACTION_MESSAGE}
        >
          Message
        </Button>
      ) : connected && state?.thread_id ? (
        <Link href={`/dashboard/messages/${state.thread_id}`}>
          <Button size={size} variant={outlineVariant}>
            Message
          </Button>
        </Link>
      ) : canMessage ? (
        <Button size={size} variant={outlineVariant} onClick={onMessageClick}>
          Message
        </Button>
      ) : (
        <Button
          size={size}
          variant={outlineVariant}
          disabled
          title={messageHint ?? "Connect first to send a message."}
          aria-disabled="true"
          className="cursor-not-allowed opacity-55"
        >
          Message
        </Button>
      )}
      {!compact && messageHint ? (
        <p className={hintClass}>{messageHint}</p>
      ) : !compact && hint ? (
        <p
          className={
            surface === "light"
              ? "max-w-xs text-xs font-semibold text-muted-foreground"
              : "max-w-xs text-xs font-semibold text-paper/70"
          }
        >
          {hint}
        </p>
      ) : null}
    </div>
  ) : null;

  const shellClass = compact
    ? "flex w-full gap-2 [&_a]:block [&_a]:w-full [&_button]:w-full"
    : "contents";
  const slotClass = compact ? "min-w-0 flex-1" : undefined;

  return (
    <div className={shellClass}>
      {connectControl ? <div className={slotClass}>{connectControl}</div> : null}
      {messageControl ? <div className={slotClass}>{messageControl}</div> : null}
      <Modal
        open={hostOpen}
        onClose={() => setHostOpen(false)}
        title="Message Fan"
        description="Only message fans you already have a relationship with. Stay on Pàdéyá."
      >
        <div className="space-y-3">
          <textarea
            value={hostBody}
            onChange={(e) => setHostBody(e.target.value.slice(0, 2000))}
            rows={4}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Write a message…"
          />
          {hostError ? (
            <p className="text-sm font-semibold text-danger">{hostError}</p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setHostOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={hostBusy || !hostBody.trim()}
              onClick={() => {
                setHostBusy(true);
                void createHostThread({
                  fan_username: username,
                  body: hostBody.trim(),
                })
                  .then((t) => {
                    setHostOpen(false);
                    router.push(`/host/messages/${t.id}`);
                  })
                  .catch((err) => setHostError(formatSelfMessageError(err)))
                  .finally(() => setHostBusy(false));
              }}
            >
              Send
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
