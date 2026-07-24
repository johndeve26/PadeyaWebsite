"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { PublicVaultItemCard } from "@/components/vault/public/PublicVaultItemCard";
import { VaultItemHostCard } from "@/components/vault/public/VaultItemHostCard";
import { VaultItemLockedPanel } from "@/components/vault/public/VaultItemLockedPanel";
import { VaultItemUnlockedContent } from "@/components/vault/public/VaultItemUnlockedContent";
import {
  Alert,
  Badge,
  Button,
  Container,
  EmptyState,
  Media,
  SectionHeader,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  trackVaultItemView,
  trackVaultUnlockClick,
  trackVaultUnlockFailed,
  trackVaultUnlockSuccess,
} from "@/lib/analytics";
import { fetchMyFollowing, followHost, unfollowHost } from "@/lib/crm-api";
import { fetchLegacyPage } from "@/lib/legacy-api";
import type { LegacyPage } from "@/lib/types/legacy";
import type { VaultCatalogCard, VaultItem } from "@/lib/types/vault";
import { formatAccessType, vaultLockMessage } from "@/lib/vault-lock-copy";
import {
  fetchPublicVault,
  fetchPublicVaultItem,
  redeemVaultInvite,
  unlockVaultItem,
} from "@/lib/vault-api";

export default function PublicVaultItemPage() {
  const params = useParams<{ username: string; itemSlug: string }>();
  const username = decodeURIComponent(params.username);
  const itemSlug = decodeURIComponent(params.itemSlug);
  const { user } = useAuth();
  const [item, setItem] = useState<VaultItem | null>(null);
  const [related, setRelated] = useState<VaultCatalogCard[]>([]);
  const [legacy, setLegacy] = useState<LegacyPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [following, setFollowing] = useState(false);
  const [followBusy, setFollowBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [data, catalog, page] = await Promise.all([
          fetchPublicVaultItem(username, itemSlug),
          fetchPublicVault(username).catch(() => [] as VaultCatalogCard[]),
          fetchLegacyPage(username).catch(() => null),
        ]);
        if (!active) return;
        setItem(data);
        setRelated(catalog.filter((row) => row.slug !== itemSlug).slice(0, 6));
        setLegacy(page);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Item not found");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [username, itemSlug]);

  useEffect(() => {
    if (!user || !legacy?.host_id) return;
    let active = true;
    void fetchMyFollowing()
      .then((rows) => {
        if (active) setFollowing(rows.some((r) => r.host_id === legacy.host_id));
      })
      .catch(() => {
        if (active) setFollowing(false);
      });
    return () => {
      active = false;
    };
  }, [user, legacy?.host_id]);

  const showFollowing = Boolean(user && legacy?.host_id && following);

  useEffect(() => {
    if (!item) return;
    const hostId = item.host_id || legacy?.host_id;
    if (!hostId) return;
    trackVaultItemView({
      hostId,
      vaultItemId: item.id,
      accessType: item.access?.access_type ?? null,
      relatedEventId: item.related_event?.id ?? item.related_event_id ?? null,
      lockedState: item.locked,
      sourcePage: "vault_item",
      listContext: "vault_item",
    });
  }, [item, legacy?.host_id]);

  function unlockMeta(row: VaultItem, failureReason?: string | null) {
    return {
      hostId: row.host_id || legacy?.host_id || "",
      vaultItemId: row.id,
      accessType: row.access?.access_type ?? null,
      relatedEventId: row.related_event?.id ?? row.related_event_id ?? null,
      lockedState: row.locked,
      sourcePage: "vault_item",
      failureReason: failureReason ?? null,
    };
  }

  async function load() {
    const data = await fetchPublicVaultItem(username, itemSlug);
    setItem(data);
    return data;
  }

  async function onUnlock() {
    if (!item) return;
    const hostId = item.host_id || legacy?.host_id;
    if (hostId) {
      trackVaultUnlockClick(unlockMeta(item));
    }
    if (!user) {
      window.location.href = `/login?next=${encodeURIComponent(`/@${username}/vault/${itemSlug}`)}`;
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const checkout = await unlockVaultItem(item.id);
      if (checkout.purchase.status === "paid") {
        const refreshed = await load();
        if (hostId) {
          trackVaultUnlockSuccess(unlockMeta(refreshed));
        }
        setNote("Drop unlocked");
      } else if (checkout.purchase.authorization_url) {
        window.location.href = checkout.purchase.authorization_url;
      }
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Unlock failed";
      if (hostId) {
        trackVaultUnlockFailed(unlockMeta(item, detail));
      }
      setError(detail);
    } finally {
      setBusy(false);
    }
  }

  async function onRedeemInvite() {
    if (!item) return;
    const hostId = item.host_id || legacy?.host_id;
    if (hostId) {
      trackVaultUnlockClick(unlockMeta(item));
    }
    if (!user) {
      window.location.href = `/login?next=${encodeURIComponent(`/@${username}/vault/${itemSlug}`)}`;
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const unlocked = await redeemVaultInvite(item.id, inviteCode);
      setItem(unlocked);
      setInviteCode("");
      if (hostId) {
        trackVaultUnlockSuccess(unlockMeta(unlocked));
      }
      setNote("Invite redeemed — drop unlocked");
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Invite redeem failed";
      if (hostId) {
        trackVaultUnlockFailed(unlockMeta(item, detail));
      }
      setError(detail);
    } finally {
      setBusy(false);
    }
  }

  async function onFollowToggle() {
    if (!legacy?.host_id) return;
    if (!user) {
      window.location.href = `/login?next=${encodeURIComponent(`/@${username}/vault/${itemSlug}`)}`;
      return;
    }
    setFollowBusy(true);
    setError(null);
    try {
      if (following) {
        await unfollowHost(legacy.host_id);
        setFollowing(false);
      } else {
        await followHost({ host_id: legacy.host_id });
        setFollowing(true);
        setNote("You’re following this host");
        // Followers-only drops may unlock immediately
        if (item?.access?.access_type === "followers_only" && item.locked) {
          const refreshed = await load();
          if (!refreshed.locked && (item.host_id || legacy.host_id)) {
            trackVaultUnlockSuccess(unlockMeta(refreshed));
          }
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Follow failed");
    } finally {
      setFollowBusy(false);
    }
  }

  const lockMessage = useMemo(
    () => (item ? vaultLockMessage(item) : null),
    [item],
  );

  if (error && !item) {
    return (
      <main className="bg-background py-20">
        <Container width="narrow">
          <EmptyState
            title="Vault item unavailable"
            description={error}
            action={
              <Link href={`/@${username}/vault`}>
                <Button variant="secondary">Back to Vault</Button>
              </Link>
            }
          />
        </Container>
      </main>
    );
  }

  if (!item) {
    return (
      <main className="bg-ink py-20">
        <Container width="narrow" className="space-y-4">
          <SkeletonLoader lines={6} />
        </Container>
      </main>
    );
  }

  const accessType = item.access?.access_type;

  return (
    <main className="bg-background pb-16">
      <section className="relative min-h-[52vh] overflow-hidden bg-ink text-paper sm:min-h-[58vh]">
        {item.cover_url ? (
          <Media
            src={item.cover_url}
            alt=""
            className="absolute inset-0 h-full w-full object-cover opacity-45 padeya-hero-media"
          />
        ) : (
          <div aria-hidden className="padeya-hero-glow absolute inset-0" />
        )}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink via-ink/60 to-ink/35"
        />

        <Container className="relative flex min-h-[52vh] flex-col justify-end pb-10 pt-16 sm:min-h-[58vh] sm:pb-14">
          <div className="padeya-hero-brand max-w-3xl space-y-4">
            <div className="flex flex-wrap gap-2">
              <Link href={`/u/${username}/vault`}>
                <Button variant="outline-dark" size="sm">
                  Back to Vault
                </Button>
              </Link>
              <Link href={`/u/${username}`}>
                <Button variant="outline-dark" size="sm">
                  Legacy Page
                </Button>
              </Link>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={item.locked ? "warning" : "success"}>
                {item.locked ? "Locked" : "Unlocked"}
              </Badge>
              <Badge tone="outline" className="border-paper/25 text-paper/80">
                {formatAccessType(accessType)}
              </Badge>
              <Badge tone="outline" className="border-paper/25 text-paper/80">
                {(item.content_type || "drop").replace(/_/g, " ")}
              </Badge>
            </div>
            <h1 className="text-balance text-3xl font-extrabold tracking-tight sm:text-5xl">
              {item.title}
            </h1>
            {item.preview_text ? (
              <p className="max-w-2xl text-pretty text-base leading-relaxed text-subtle-foreground sm:text-lg">
                {item.preview_text}
              </p>
            ) : null}
            {item.locked && lockMessage ? (
              <p className="text-sm font-semibold text-accent sm:text-base">
                {lockMessage}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {item.related_event ? (
                <Link
                  href={item.related_event.href}
                  className="inline-flex text-sm font-semibold text-subtle-foreground underline-offset-2 hover:text-accent hover:underline"
                >
                  Related event · {item.related_event.title}
                </Link>
              ) : null}
              {item.related_memory ? (
                <Link
                  href={item.related_memory.href}
                  className="inline-flex text-sm font-semibold text-subtle-foreground underline-offset-2 hover:text-accent hover:underline"
                >
                  Event Memory · {item.related_memory.event_title}
                </Link>
              ) : null}
              <Link
                href={`/u/${username}`}
                className="inline-flex text-sm font-semibold text-subtle-foreground underline-offset-2 hover:text-accent hover:underline"
              >
                Host Legacy Page
              </Link>
            </div>
          </div>
        </Container>
      </section>

      <Container className="py-10 sm:py-12">
        {error ? (
          <Alert tone="danger" title="Something went wrong" className="mb-6">
            {error}
          </Alert>
        ) : null}
        {note ? (
          <Alert tone="success" title="Updated" className="mb-6">
            {note}
          </Alert>
        ) : null}
        {item.expired ? (
          <Alert tone="warning" title="This drop has expired" className="mb-6">
            Unlock access is no longer available for this Vault item.
          </Alert>
        ) : null}

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start">
          <div className="space-y-8">
            {item.locked ? (
              <VaultItemLockedPanel
                item={item}
                username={username}
                itemSlug={itemSlug}
                hostId={item.host_id || legacy?.host_id}
                userLoggedIn={Boolean(user)}
                busy={busy}
                inviteCode={inviteCode}
                onInviteCodeChange={setInviteCode}
                onUnlock={() => void onUnlock()}
                onRedeemInvite={() => void onRedeemInvite()}
                onFollow={() => void onFollowToggle()}
                followBusy={followBusy}
                following={showFollowing}
                followEnabled={legacy?.follow_enabled !== false}
              />
            ) : (
              <VaultItemUnlockedContent
                item={item}
                hostId={item.host_id || legacy?.host_id}
                sourcePage="vault_item"
              />
            )}

            {item.locked && (item.related_event || item.related_memory) ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {item.related_event ? (
                  <section className="rounded-[var(--radius-xl)] border border-border bg-muted/60 px-5 py-5">
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                      Related event
                    </p>
                    <p className="mt-2 text-lg font-extrabold text-foreground">
                      {item.related_event.title}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Ticket or attendance for this event may unlock the drop.
                    </p>
                    <Link href={item.related_event.href} className="mt-4 inline-flex">
                      <Button size="sm">View event</Button>
                    </Link>
                  </section>
                ) : null}
                {item.related_memory ? (
                  <section className="rounded-[var(--radius-xl)] border border-border bg-muted/60 px-5 py-5">
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                      Related memory
                    </p>
                    <p className="mt-2 text-lg font-extrabold text-foreground">
                      {item.related_memory.event_title}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      See the public Event Memory for this night.
                    </p>
                    <Link href={item.related_memory.href} className="mt-4 inline-flex">
                      <Button size="sm">View memory</Button>
                    </Link>
                  </section>
                ) : null}
              </div>
            ) : null}
          </div>

          <VaultItemHostCard
            username={username}
            legacy={legacy}
            following={showFollowing}
            followBusy={followBusy}
            onFollow={() => void onFollowToggle()}
          />
        </div>

        {related.length > 0 ? (
          <section className="mt-14 space-y-6">
            <SectionHeader
              eyebrow="More from this Vault"
              title="Related Vault drops"
              description={`More exclusive content from ${legacy?.display_name || username}.`}
            />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {related.map((row, index) => (
                <PublicVaultItemCard
                  key={row.id}
                  item={row}
                  username={username}
                  hostId={item.host_id || legacy?.host_id}
                  sourcePage="vault_item"
                  listContext="vault_related"
                  cardPosition={index}
                />
              ))}
            </div>
            <Link href={`/u/${username}/vault`}>
              <Button variant="secondary">Browse full Vault</Button>
            </Link>
          </section>
        ) : null}
      </Container>
    </main>
  );
}
