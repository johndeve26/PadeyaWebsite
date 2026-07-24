"use client";

import Link from "next/link";

import {
  Alert,
  Button,
  Card,
  Input,
  Media,
} from "@/components/ui";
import {
  trackVaultFollowUnlock,
  trackVaultTicketUnlock,
} from "@/lib/analytics";
import { formatNgn } from "@/lib/format";
import type { VaultItem } from "@/lib/types/vault";
import { vaultLockMessage } from "@/lib/vault-lock-copy";

type Props = {
  item: VaultItem;
  username: string;
  itemSlug: string;
  hostId?: string | null;
  userLoggedIn: boolean;
  busy: boolean;
  inviteCode: string;
  onInviteCodeChange: (value: string) => void;
  onUnlock: () => void;
  onRedeemInvite: () => void;
  onFollow: () => void;
  followBusy: boolean;
  following: boolean;
  followEnabled: boolean;
};

export function VaultItemLockedPanel({
  item,
  username,
  itemSlug,
  hostId = null,
  userLoggedIn,
  busy,
  inviteCode,
  onInviteCodeChange,
  onUnlock,
  onRedeemInvite,
  onFollow,
  followBusy,
  following,
  followEnabled,
}: Props) {
  const accessType = item.access?.access_type;
  const message = vaultLockMessage(item);
  const canUnlockPaid = accessType === "one_time_unlock" && !item.expired;
  const canRedeemInvite = accessType === "invite_only" && !item.expired;
  const needsFollow = accessType === "followers_only" && !item.expired;
  const needsTicket =
    (accessType === "ticket_holder_only" ||
      accessType === "checked_in_attendee_only" ||
      accessType === "vip_ticket_holder_only") &&
    !item.expired;
  const previewMedia = (item.media || []).filter((m) => m.is_preview && m.url);
  const loginHref = `/login?next=${encodeURIComponent(`/@${username}/vault/${itemSlug}`)}`;
  const price = item.access?.price ?? item.price;

  function vaultMeta() {
    return {
      hostId: hostId || item.host_id,
      vaultItemId: item.id,
      accessType: accessType ?? null,
      relatedEventId: item.related_event?.id ?? item.related_event_id ?? null,
      lockedState: true as const,
      sourcePage: "vault_item",
    };
  }

  function onFollowClick() {
    if (hostId || item.host_id) {
      trackVaultFollowUnlock(vaultMeta());
    }
    onFollow();
  }

  function onTicketUnlockClick() {
    if (hostId || item.host_id) {
      trackVaultTicketUnlock(vaultMeta());
    }
  }

  return (
    <Card className="space-y-5 border-border shadow-[var(--shadow)]">
      <div className="space-y-2">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
          Locked preview
        </p>
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground">
          {message}
        </h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Full body, private media, downloads, and external links stay protected
          until access is granted.
        </p>
      </div>

      <Alert tone="info" title="Protected by Pàdéyá">
        Private Vault content is never sent to the browser while locked.
      </Alert>

      {canUnlockPaid ? (
        <div className="flex flex-wrap items-center gap-4 rounded-[var(--radius-lg)] border border-primary/35 bg-surface-inset px-4 py-4 shadow-[var(--shadow-soft)]">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
              One-time unlock
            </p>
            <p className="text-2xl font-extrabold text-heading">
              {formatNgn(price)}
            </p>
          </div>
          <Button size="lg" disabled={busy} onClick={onUnlock}>
            {busy ? "Starting checkout…" : `Unlock for ${formatNgn(price)}`}
          </Button>
          {!userLoggedIn ? (
            <Link href={loginHref}>
              <Button size="lg" variant="ghost">
                Sign in
              </Button>
            </Link>
          ) : null}
        </div>
      ) : null}

      {canRedeemInvite ? (
        <div className="space-y-3 rounded-[var(--radius-lg)] border border-border bg-surface-inset px-4 py-4">
          <Input
            label="Access code"
            value={inviteCode}
            onChange={(e) => onInviteCodeChange(e.target.value)}
            placeholder="Enter invite code"
            autoComplete="off"
          />
          <div className="flex flex-wrap gap-2">
            <Button
              size="lg"
              disabled={busy || !inviteCode.trim()}
              onClick={onRedeemInvite}
            >
              {busy ? "Redeeming…" : "Redeem invite"}
            </Button>
            {!userLoggedIn ? (
              <Link href={loginHref}>
                <Button size="lg" variant="secondary">
                  Sign in
                </Button>
              </Link>
            ) : null}
          </div>
        </div>
      ) : null}

      {needsFollow ? (
        <div className="flex flex-wrap gap-2">
          {followEnabled ? (
            <Button
              size="lg"
              disabled={followBusy || following}
              onClick={onFollowClick}
            >
              {following ? "Following" : "Follow this host"}
            </Button>
          ) : null}
          <Link href={`/@${username}`}>
            <Button size="lg" variant="secondary">
              View Legacy Page
            </Button>
          </Link>
          {!userLoggedIn ? (
            <Link href={loginHref}>
              <Button size="lg" variant="ghost">
                Sign in
              </Button>
            </Link>
          ) : null}
        </div>
      ) : null}

      {needsTicket ? (
        <div className="flex flex-wrap gap-2">
          {item.related_event ? (
            <Link href={item.related_event.href} onClick={onTicketUnlockClick}>
              <Button size="lg">
                {accessType === "checked_in_attendee_only"
                  ? "View event"
                  : "Buy a ticket"}
              </Button>
            </Link>
          ) : (
            <Link href={`/@${username}`} onClick={onTicketUnlockClick}>
              <Button size="lg">Browse host events</Button>
            </Link>
          )}
          {!userLoggedIn ? (
            <Link href={loginHref}>
              <Button size="lg" variant="secondary">
                Sign in
              </Button>
            </Link>
          ) : null}
        </div>
      ) : null}

      {!canUnlockPaid &&
      !canRedeemInvite &&
      !needsFollow &&
      !needsTicket &&
      !item.expired ? (
        <div className="flex flex-wrap gap-2">
          {!userLoggedIn ? (
            <Link href={loginHref}>
              <Button size="lg">Sign in to unlock</Button>
            </Link>
          ) : null}
          <Link href={`/@${username}/vault`}>
            <Button size="lg" variant="secondary">
              Back to Vault
            </Button>
          </Link>
        </div>
      ) : null}

      {item.related_event && needsTicket ? (
        <p className="text-sm text-muted-foreground">
          Related event ·{" "}
          <Link
            href={item.related_event.href}
            className="font-semibold text-foreground underline-offset-2 hover:underline"
          >
            {item.related_event.title}
          </Link>
        </p>
      ) : null}

      {previewMedia.length > 0 ? (
        <div className="space-y-3 border-t border-border pt-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Public preview
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {previewMedia.map((m) =>
              m.media_type === "image" && m.url ? (
                <div
                  key={m.id}
                  className="relative aspect-[16/10] overflow-hidden rounded-[var(--radius-md)] bg-surface-dark"
                >
                  <Media src={m.url} alt={m.label || ""} className="h-full w-full object-cover" />
                </div>
              ) : (
                <a
                  key={m.id}
                  className="text-sm font-semibold text-foreground underline-offset-2 hover:underline"
                  href={m.url!}
                  target="_blank"
                  rel="noreferrer"
                >
                  {m.label || m.media_type}
                </a>
              ),
            )}
          </div>
        </div>
      ) : (
        <div className="rounded-[var(--radius-md)] border border-dashed border-border-strong/50 bg-surface-inset px-4 py-8 text-center text-sm font-medium text-muted-foreground">
          Locked content placeholder — private files are not shown here.
        </div>
      )}
    </Card>
  );
}
