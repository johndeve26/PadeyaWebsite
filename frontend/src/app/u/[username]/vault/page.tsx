"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { VaultDefinitionNote } from "@/components/vault/VaultDefinitionNote";
import { PublicVaultItemCard } from "@/components/vault/public/PublicVaultItemCard";
import {
  Alert,
  Badge,
  Button,
  Container,
  EmptyState,
  Media,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { trackVaultPageView } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import { fetchMyFollowing, followHost, unfollowHost } from "@/lib/crm-api";
import { fetchLegacyPage } from "@/lib/legacy-api";
import type { LegacyPage } from "@/lib/types/legacy";
import type { VaultCatalogCard } from "@/lib/types/vault";
import {
  VAULT_EXAMPLES,
  VAULT_PUBLIC_DESCRIPTION,
  VAULT_UNLOCK_PATHS,
  vaultPublicHeadline,
} from "@/lib/vault-copy";
import { formatAccessType } from "@/lib/vault-lock-copy";
import { fetchPublicVault } from "@/lib/vault-api";

type AccessFilter = "all" | string;
type ContentFilter = "all" | string;

function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

export default function PublicVaultPage() {
  const params = useParams<{ username: string }>();
  const username = decodeURIComponent(params.username);
  const { user } = useAuth();
  const [items, setItems] = useState<VaultCatalogCard[] | null>(null);
  const [legacy, setLegacy] = useState<LegacyPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accessFilter, setAccessFilter] = useState<AccessFilter>("all");
  const [contentFilter, setContentFilter] = useState<ContentFilter>("all");
  const [following, setFollowing] = useState(false);
  const [followBusy, setFollowBusy] = useState(false);
  const [followNote, setFollowNote] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [rows, page] = await Promise.all([
          fetchPublicVault(username),
          fetchLegacyPage(username).catch(() => null),
        ]);
        if (!active) return;
        setItems(rows);
        setLegacy(page);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Vault unavailable");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [username]);

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
    if (!legacy?.host_id || !items) return;
    trackVaultPageView({
      hostId: legacy.host_id,
      sourcePage: "vault_catalog",
      listContext: "vault_catalog",
    });
  }, [legacy?.host_id, items]);

  const displayName = legacy?.display_name || username;
  const coverUrl = legacy?.profile?.cover_url || null;
  const avatarUrl = legacy?.profile?.avatar_url || null;
  const featured =
    items?.find((item) => item.featured) ||
    items?.find((item) => item.cover_url) ||
    items?.[0] ||
    null;

  const accessTypes = useMemo(() => {
    const set = new Set(
      (items || [])
        .map((i) => i.access_type)
        .filter((type): type is string => Boolean(type)),
    );
    return Array.from(set).sort();
  }, [items]);

  const contentTypes = useMemo(() => {
    const set = new Set(
      (items || [])
        .map((i) => i.content_type)
        .filter((type): type is string => Boolean(type)),
    );
    return Array.from(set).sort();
  }, [items]);

  const filtered = useMemo(() => {
    if (!items) return [];
    return items.filter((item) => {
      if (accessFilter !== "all" && item.access_type !== accessFilter) return false;
      if (contentFilter !== "all" && item.content_type !== contentFilter) return false;
      return true;
    });
  }, [items, accessFilter, contentFilter]);

  const gridItems = useMemo(() => {
    if (!featured) return filtered;
    return filtered.filter((item) => item.id !== featured.id);
  }, [filtered, featured]);

  const lockedCount = items?.filter((i) => i.locked).length ?? 0;
  const unlockedCount = items?.filter((i) => !i.locked).length ?? 0;

  async function onFollowToggle() {
    if (!legacy?.host_id) return;
    if (!user) {
      window.location.href = `/login?next=${encodeURIComponent(`/@${username}/vault`)}`;
      return;
    }
    setFollowBusy(true);
    setFollowNote(null);
    try {
      if (following) {
        await unfollowHost(legacy.host_id);
        setFollowing(false);
        setFollowNote("Unfollowed");
      } else {
        await followHost({ host_id: legacy.host_id });
        setFollowing(true);
        setFollowNote("You’re following this host");
      }
    } catch (err) {
      setFollowNote(err instanceof ApiError ? err.detail : "Follow failed");
    } finally {
      setFollowBusy(false);
    }
  }

  return (
    <main className="bg-background">
      {/* Hero — Legacy-connected exclusive surface */}
      <section className="relative min-h-[72vh] overflow-hidden bg-ink text-paper sm:min-h-[78vh]">
        {coverUrl ? (
          <Media
            src={coverUrl}
            alt=""
            className="absolute inset-0 h-full w-full object-cover opacity-45 padeya-hero-media"
          />
        ) : (
          <div aria-hidden className="padeya-hero-glow absolute inset-0" />
        )}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink via-ink/55 to-ink/30"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-ink to-transparent"
        />

        <Container className="relative flex min-h-[72vh] flex-col justify-end pb-12 pt-20 sm:min-h-[78vh] sm:pb-16">
          <div className="padeya-hero-brand max-w-2xl space-y-5">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">
              Vault · @{username}
            </p>
            <h1 className="text-balance text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
              {vaultPublicHeadline(displayName)}
            </h1>
            <p className="max-w-xl text-pretty text-base leading-relaxed text-subtle-foreground sm:text-lg">
              {VAULT_PUBLIC_DESCRIPTION}
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              {legacy?.follow_enabled !== false ? (
                <Button
                  size="lg"
                  disabled={followBusy || !legacy?.host_id}
                  onClick={() => void onFollowToggle()}
                >
                  {showFollowing ? "Following" : "Follow host"}
                </Button>
              ) : null}
              <Link href={`/@${username}`}>
                <Button size="lg" variant="outline-dark">
                  View Legacy Page
                </Button>
              </Link>
            </div>
          </div>
        </Container>
      </section>

      {/* Host identity strip */}
      <section className="border-b border-border bg-muted/70">
        <Container className="flex flex-col gap-4 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full border border-border bg-ink sm:h-16 sm:w-16">
              {avatarUrl ? (
                <Media src={avatarUrl} alt="" className="h-full w-full object-cover" />
              ) : (
                <span className="flex h-full w-full items-center justify-center text-lg font-extrabold text-accent">
                  {displayName.slice(0, 1).toUpperCase()}
                </span>
              )}
            </div>
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="truncate text-xl font-extrabold text-foreground">
                  {displayName}
                </h2>
                {legacy?.verified ? <Badge tone="accent">Verified</Badge> : null}
                {legacy?.tier?.name ? (
                  <Badge tone="dark">{legacy.tier.name}</Badge>
                ) : null}
              </div>
              <p className="text-sm text-muted-foreground">
                @{username}
                {legacy?.tagline ? ` · ${legacy.tagline}` : " · Host on Pàdéyá"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {legacy?.follow_enabled !== false ? (
              <Button
                size="sm"
                variant={showFollowing ? "secondary" : "primary"}
                disabled={followBusy || !legacy?.host_id}
                onClick={() => void onFollowToggle()}
              >
                {showFollowing ? "Following" : "Follow"}
              </Button>
            ) : null}
            <Link href={`/@${username}`}>
              <Button size="sm" variant="ghost">
                Legacy Page
              </Button>
            </Link>
          </div>
        </Container>
        {followNote ? (
          <Container className="pb-4">
            <p className="text-sm text-muted-foreground">{followNote}</p>
          </Container>
        ) : null}
      </section>

      <Container className="space-y-14 py-12 sm:py-16">
        {/* Vault explanation */}
        <section className="grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-end">
          <div className="space-y-4">
            <SectionHeader
              eyebrow="What is Vault"
              title="Exclusive content, unlocked your way"
              description="Previews are free. Full drops unlock when you follow, buy a ticket, check in, hold VIP access, or make a one-time purchase."
            />
            <VaultDefinitionNote compact />
          </div>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            {VAULT_UNLOCK_PATHS.map((path, index) => (
              <li
                key={path}
                className="flex items-start gap-3 border-l-2 border-accent pl-3 text-sm text-muted-foreground"
                style={{ animationDelay: `${index * 60}ms` }}
              >
                <span className="font-semibold text-foreground">{path}</span>
              </li>
            ))}
          </ul>
        </section>

        {error ? (
          <Alert tone="danger" title="Vault unavailable">
            {error}
          </Alert>
        ) : null}

        {!items ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : null}

        {items && items.length === 0 ? (
          <div className="space-y-6">
            <EmptyState
              title="No Vault drops yet"
              description={`${displayName} hasn’t published exclusive content yet. Vault drops can include:`}
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  <Link href={`/@${username}`}>
                    <Button>View Legacy Page</Button>
                  </Link>
                  {legacy?.follow_enabled !== false ? (
                    <Button
                      variant="secondary"
                      disabled={followBusy || !legacy?.host_id}
                      onClick={() => void onFollowToggle()}
                    >
                      {showFollowing ? "Following" : "Follow host"}
                    </Button>
                  ) : null}
                </div>
              }
            />
            <ul className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
              {VAULT_EXAMPLES.map((example) => (
                <li key={example} className="flex gap-2">
                  <span className="text-accent" aria-hidden>
                    ·
                  </span>
                  <span>{example}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {items && items.length > 0 ? (
          <>
            {/* Featured drop */}
            {featured &&
            (accessFilter === "all" || featured.access_type === accessFilter) &&
            (contentFilter === "all" || featured.content_type === contentFilter) ? (
              <section className="space-y-5">
                <SectionHeader
                  eyebrow="Featured"
                  title="Featured Vault drop"
                  description="Pinned from this host’s Legacy Page — start here."
                />
                <PublicVaultItemCard
                  item={featured}
                  username={username}
                  featured
                  hostId={legacy?.host_id}
                  sourcePage="vault_catalog"
                  listContext="vault_catalog"
                  cardPosition={0}
                />
              </section>
            ) : null}

            {/* Filters + grid */}
            <section className="space-y-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <SectionHeader
                  title="All drops"
                  description={`${filtered.length} shown · ${unlockedCount} unlocked · ${lockedCount} locked`}
                />
                <div className="flex flex-wrap gap-2">
                  <Link href={`/@${username}`}>
                    <Button size="sm" variant="secondary">
                      View Legacy Page
                    </Button>
                  </Link>
                  {legacy?.follow_enabled !== false ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={followBusy || !legacy?.host_id}
                      onClick={() => void onFollowToggle()}
                    >
                      {showFollowing ? "Following" : "Follow host"}
                    </Button>
                  ) : null}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                    Access type
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <FilterChip
                      active={accessFilter === "all"}
                      label="All access"
                      count={items.length}
                      onClick={() => setAccessFilter("all")}
                    />
                    {accessTypes.map((type) => (
                      <FilterChip
                        key={type}
                        active={accessFilter === type}
                        label={formatAccessType(type)}
                        count={items.filter((i) => i.access_type === type).length}
                        onClick={() => setAccessFilter(type)}
                      />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                    Content type
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <FilterChip
                      active={contentFilter === "all"}
                      label="All types"
                      count={items.length}
                      onClick={() => setContentFilter("all")}
                    />
                    {contentTypes.map((type) => (
                      <FilterChip
                        key={type}
                        active={contentFilter === type}
                        label={formatLabel(type)}
                        count={items.filter((i) => i.content_type === type).length}
                        onClick={() => setContentFilter(type)}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {filtered.length === 0 ? (
                <EmptyState
                  title="No drops match these filters"
                  description="Try another access or content type."
                  action={
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setAccessFilter("all");
                        setContentFilter("all");
                      }}
                    >
                      Clear filters
                    </Button>
                  }
                />
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {(featured &&
                  (accessFilter === "all" || featured.access_type === accessFilter) &&
                  (contentFilter === "all" || featured.content_type === contentFilter)
                    ? gridItems
                    : filtered
                  ).map((item, index) => (
                    <PublicVaultItemCard
                      key={item.id}
                      item={item}
                      username={username}
                      hostId={legacy?.host_id}
                      sourcePage="vault_catalog"
                      listContext="vault_catalog"
                      cardPosition={index}
                    />
                  ))}
                </div>
              )}
            </section>

            {/* Closing CTAs */}
            <section className="overflow-hidden rounded-[var(--radius-xl)] bg-ink px-6 py-10 text-paper sm:px-10">
              <div className="relative space-y-4">
                <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-60" />
                <div className="relative space-y-4">
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
                    Stay close
                  </p>
                  <h2 className="max-w-xl text-2xl font-extrabold tracking-tight sm:text-3xl">
                    Follow {displayName} and explore their Legacy
                  </h2>
                  <p className="max-w-lg text-sm leading-relaxed text-subtle-foreground sm:text-base">
                    New Vault drops, ticket-holder rewards, and host stories live on
                    their Legacy Page.
                  </p>
                  <div className="flex flex-wrap gap-3 pt-1">
                    {legacy?.follow_enabled !== false ? (
                      <Button
                        size="lg"
                        disabled={followBusy || !legacy?.host_id}
                        onClick={() => void onFollowToggle()}
                      >
                        {showFollowing ? "Following" : "Follow host"}
                      </Button>
                    ) : null}
                    <Link href={`/@${username}`}>
                      <Button size="lg" variant="outline-dark">
                        View Legacy Page
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            </section>
          </>
        ) : null}
      </Container>
    </main>
  );
}

function FilterChip({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean;
  label: string;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-[var(--radius-md)] border px-3 py-1.5 text-sm font-semibold transition-colors",
        active
          ? "border-ink bg-ink text-paper"
          : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-foreground",
      )}
    >
      {label}
      <span className="ml-1.5 tabular-nums opacity-70">{count}</span>
    </button>
  );
}
