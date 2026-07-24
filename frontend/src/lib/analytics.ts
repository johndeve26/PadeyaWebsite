/**
 * Robust client analytics: UTM persistence, queued/batched writes, never block UX.
 * Transport lives in analytics-api; taxonomy in analytics-taxonomy.
 */

import {
  assertClientActionAllowed,
  generateDedupeKey,
  getOrCreateAnonymousId,
  getOrCreateSessionId,
  isLikelyBot,
  normalizeUtmParams,
} from "@/lib/analytics-client";
import { trackBatch as apiTrackBatch } from "@/lib/analytics-api";
import {
  TrackedAction,
  normalizeTrackedAction,
  type AnalyticsDimensions,
  type AnalyticsEventMetadata,
  type TrackedActionName,
} from "@/lib/analytics-taxonomy";

export type ListContext =
  | "homepage_featured"
  | "homepage_nearby"
  | "events_grid"
  | "category_page"
  | "city_page"
  | "legacy_upcoming"
  | "search_results"
  | "sponsor_related"
  | "demo_page"
  | "related_events"
  | "event_detail"
  | (string & {});

const UTM_STORAGE_KEY = "padeya_utm_attribution";
const DEDUPE_STORAGE_KEY = "padeya_analytics_dedupe";
const QUEUE_STORAGE_KEY = "padeya_analytics_queue";

const BATCH_SIZE = 12;
const BATCH_FLUSH_MS = 2500;
const MAX_RETRIES = 4;
const IMPRESSION_VISIBLE_RATIO = 0.5;
const IMPRESSION_DWELL_MS = 500;

export type QueuedEvent = {
  id: string;
  trackedAction: string;
  targetEventId?: string;
  eventListingId?: string;
  hostId?: string;
  metadata?: AnalyticsEventMetadata;
  dimensions?: AnalyticsDimensions;
  attempts: number;
  createdAt: number;
};

type UtmBag = {
  source?: string;
  medium?: string;
  campaign?: string;
  term?: string;
  content?: string;
  landingPage?: string;
  capturedAt: string;
};

let flushTimer: ReturnType<typeof setTimeout> | null = null;
let flushing = false;
const memoryDedupe = new Set<string>();

function safeStorage(kind: "local" | "session"): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return kind === "local" ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
}

function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `q${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

/** Capture UTM from the current URL and persist for the session. */
export function captureUtmAttribution(url?: string): UtmBag {
  const href =
    url ?? (typeof window !== "undefined" ? window.location.href : undefined);
  const utm = normalizeUtmParams(undefined, href);
  const store = safeStorage("session");
  const existing = readUtmAttribution();
  const hasNew = Boolean(
    utm.source || utm.medium || utm.campaign || utm.term || utm.content,
  );
  const next: UtmBag = hasNew
    ? {
        source: utm.source,
        medium: utm.medium,
        campaign: utm.campaign,
        term: utm.term,
        content: utm.content,
        landingPage:
          typeof window !== "undefined"
            ? `${window.location.pathname}${window.location.search}`
            : existing?.landingPage,
        capturedAt: new Date().toISOString(),
      }
    : existing ?? {
        landingPage:
          typeof window !== "undefined" ? window.location.pathname : undefined,
        capturedAt: new Date().toISOString(),
      };

  if (store) {
    try {
      store.setItem(UTM_STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* ignore quota */
    }
  }
  return next;
}

export function readUtmAttribution(): UtmBag | null {
  const store = safeStorage("session");
  if (!store) return null;
  try {
    const raw = store.getItem(UTM_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as UtmBag;
  } catch {
    return null;
  }
}

function baseDimensions(
  extra?: AnalyticsDimensions,
): AnalyticsDimensions {
  const utm = readUtmAttribution();
  return {
    anonymousId: getOrCreateAnonymousId(),
    sessionId: getOrCreateSessionId(),
    source: extra?.source ?? utm?.source,
    medium: extra?.medium ?? utm?.medium,
    campaign: extra?.campaign ?? utm?.campaign,
    term: extra?.term ?? utm?.term,
    content: extra?.content ?? utm?.content,
    utmSource: extra?.utmSource ?? utm?.source,
    utmMedium: extra?.utmMedium ?? utm?.medium,
    utmCampaign: extra?.utmCampaign ?? utm?.campaign,
    utmTerm: extra?.utmTerm ?? utm?.term,
    utmContent: extra?.utmContent ?? utm?.content,
    landingPage: extra?.landingPage ?? utm?.landingPage,
    path:
      extra?.path ??
      (typeof window !== "undefined" ? window.location.pathname : undefined),
    currentPath:
      extra?.currentPath ??
      (typeof window !== "undefined" ? window.location.pathname : undefined),
    referrer:
      extra?.referrer ??
      (typeof document !== "undefined" ? document.referrer || undefined : undefined),
    userAgent:
      extra?.userAgent ??
      (typeof navigator !== "undefined" ? navigator.userAgent : undefined),
    isBot: extra?.isBot ?? isLikelyBot(),
    occurredAt: extra?.occurredAt ?? new Date().toISOString(),
    ...extra,
  };
}

function readQueue(): QueuedEvent[] {
  const store = safeStorage("local");
  if (!store) return [];
  try {
    const raw = store.getItem(QUEUE_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as QueuedEvent[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeQueue(items: QueuedEvent[]): void {
  const store = safeStorage("local");
  if (!store) return;
  try {
    store.setItem(QUEUE_STORAGE_KEY, JSON.stringify(items.slice(0, 200)));
  } catch {
    /* ignore */
  }
}

function scheduleFlush(delay = BATCH_FLUSH_MS): void {
  if (typeof window === "undefined") return;
  if (flushTimer) clearTimeout(flushTimer);
  flushTimer = setTimeout(() => {
    void flushQueue();
  }, delay);
}

async function flushQueue(): Promise<void> {
  if (flushing || typeof window === "undefined") return;
  const queue = readQueue();
  if (!queue.length) return;
  flushing = true;
  try {
    const batch = queue.slice(0, BATCH_SIZE);
    const rest = queue.slice(BATCH_SIZE);
    try {
      await apiTrackBatch(
        batch.map((item) => ({
          trackedAction: item.trackedAction,
          targetEventId: item.targetEventId,
          hostId: item.hostId,
          properties: item.metadata as Record<string, unknown> | undefined,
          dimensions: baseDimensions({
            ...item.dimensions,
            metadata: item.metadata,
          }),
        })),
      );
      writeQueue(rest);
      if (rest.length) scheduleFlush(800);
    } catch {
      const retried = batch.map((item) => ({
        ...item,
        attempts: item.attempts + 1,
      }));
      const keep = retried.filter((item) => item.attempts < MAX_RETRIES);
      writeQueue([...keep, ...rest]);
      if (keep.length || rest.length) {
        scheduleFlush(Math.min(30_000, 2000 * 2 ** (batch[0]?.attempts ?? 0)));
      }
    }
  } finally {
    flushing = false;
  }
}

function claimClientDedupe(key: string | null, ttlMs: number): boolean {
  if (!key) return true;
  if (memoryDedupe.has(key)) return false;
  const store = safeStorage("session");
  const now = Date.now();
  try {
    const raw = store?.getItem(DEDUPE_STORAGE_KEY);
    const map = raw ? (JSON.parse(raw) as Record<string, number>) : {};
    const expires = map[key];
    if (expires && expires > now) {
      memoryDedupe.add(key);
      return false;
    }
    map[key] = now + ttlMs;
    // prune
    for (const [k, exp] of Object.entries(map)) {
      if (exp <= now) delete map[k];
    }
    store?.setItem(DEDUPE_STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* continue */
  }
  memoryDedupe.add(key);
  return true;
}

/** Claim a client-side dedupe slot. Returns false if still within TTL. */
export function claimAnalyticsDedupe(key: string | null, ttlMs: number): boolean {
  return claimClientDedupe(key, ttlMs);
}

export type TrackOptions = {
  targetEventId?: string;
  eventListingId?: string;
  hostId?: string;
  metadata?: AnalyticsEventMetadata;
  dimensions?: AnalyticsDimensions;
  /** When true, send immediately (still never throws). */
  immediate?: boolean;
  /** Client-side dedupe window (ms). */
  dedupeTtlMs?: number;
  dedupeScope?: string;
  listContext?: ListContext;
};

/** Fire-and-forget track — never throws, never blocks UX. */
export function track(
  action: TrackedActionName | string,
  options: TrackOptions = {},
): void {
  try {
    if (typeof window === "undefined") return;
    const normalized = normalizeTrackedAction(action);
    assertClientActionAllowed(normalized);

    const metadata: AnalyticsEventMetadata = {
      ...(options.metadata ?? {}),
      ...(options.listContext ? { list_context: options.listContext } : {}),
    };

    const dedupeKey = generateDedupeKey(options.dedupeScope ?? normalized, {
      targetEventId: options.targetEventId,
      sessionId: getOrCreateSessionId(),
      anonymousId: getOrCreateAnonymousId(),
      listContext: options.listContext ?? metadata.list_context,
      extra: options.eventListingId,
    });
    if (
      options.dedupeTtlMs &&
      !claimClientDedupe(dedupeKey, options.dedupeTtlMs)
    ) {
      return;
    }

    const item: QueuedEvent = {
      id: randomId(),
      trackedAction: normalized,
      targetEventId: options.targetEventId,
      eventListingId: options.eventListingId ?? options.targetEventId,
      hostId: options.hostId,
      metadata,
      dimensions: baseDimensions(options.dimensions),
      attempts: 0,
      createdAt: Date.now(),
    };

    if (options.immediate) {
      void flushOne(item);
      return;
    }

    const queue = readQueue();
    queue.push(item);
    writeQueue(queue);
    if (queue.length >= BATCH_SIZE) scheduleFlush(0);
    else scheduleFlush();
  } catch {
    /* never block UX */
  }
}

async function flushOne(item: QueuedEvent): Promise<void> {
  try {
    await apiTrackBatch([
      {
        trackedAction: item.trackedAction,
        targetEventId: item.targetEventId,
        hostId: item.hostId,
        properties: item.metadata as Record<string, unknown> | undefined,
        dimensions: baseDimensions({
          ...item.dimensions,
          metadata: item.metadata,
        }),
      },
    ]);
  } catch {
    const queue = readQueue();
    queue.push({ ...item, attempts: item.attempts + 1 });
    writeQueue(queue);
    scheduleFlush(4000);
  }
}

/** Flush pending queue (call on visibilitychange / beforeunload). */
export function flushAnalytics(): void {
  scheduleFlush(0);
  void flushQueue();
}

let analyticsInitialized = false;

export function initAnalytics(): void {
  if (typeof window === "undefined" || analyticsInitialized) return;
  analyticsInitialized = true;
  captureUtmAttribution();
  getOrCreateAnonymousId();
  getOrCreateSessionId();
  scheduleFlush(500);

  const onHide = () => {
    if (document.visibilityState === "hidden") flushAnalytics();
  };
  document.addEventListener("visibilitychange", onHide);
  window.addEventListener("pagehide", flushAnalytics);
}

/* ---------- Convenience trackers ---------- */

export function trackPageView(opts: {
  path?: string;
  targetEventId?: string;
  hostId?: string;
  trackedAction?: string;
}): void {
  const path =
    opts.path ??
    (typeof window !== "undefined" ? window.location.pathname : "/");
  const action =
    opts.trackedAction ??
    (opts.targetEventId
      ? TrackedAction.EVENT_DETAIL_VIEW
      : TrackedAction.EVENT_LIST_VIEW);
  track(action, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    dedupeScope: opts.targetEventId ? "detail_view" : "page_view",
    dedupeTtlMs: opts.targetEventId ? 30 * 60_000 : 5_000,
    dimensions: { path, currentPath: path },
    metadata: { path },
  });
}

export function trackEventCardImpression(opts: {
  targetEventId: string;
  hostId?: string;
  listContext: ListContext;
  cardPosition?: number;
}): void {
  track(TrackedAction.EVENT_CARD_IMPRESSION, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    listContext: opts.listContext,
    dedupeScope: "impression",
    dedupeTtlMs: 5 * 60_000,
    metadata: {
      list_context: opts.listContext,
      card_position: opts.cardPosition,
    },
  });
}

export function trackEventCardClick(opts: {
  targetEventId: string;
  hostId?: string;
  listContext?: ListContext;
  clickTarget?: string;
}): void {
  track(TrackedAction.EVENT_CARD_CLICK, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    listContext: opts.listContext,
    immediate: true,
    metadata: {
      list_context: opts.listContext,
      click_target: opts.clickTarget ?? "card",
    },
  });
}

export type LocationAnalyticsMeta = {
  country?: string;
  state?: string;
  city?: string;
  area?: string;
  category?: string;
};

export type PlacementAnalyticsMeta = LocationAnalyticsMeta & {
  placementContext: string;
  slotNumber: 1 | 2;
  eventId: string;
  /** When true, also emit featured_placement_* (admin-sourced pick). */
  fromPlacement?: boolean;
};

function locationMetadata(
  meta?: LocationAnalyticsMeta,
): AnalyticsEventMetadata {
  if (!meta) return {};
  return {
    country: meta.country,
    state: meta.state,
    city: meta.city,
    area: meta.area,
    category: meta.category,
  };
}

export function trackLocationFilterUsed(meta?: LocationAnalyticsMeta): void {
  track(TrackedAction.LOCATION_FILTER_USED, {
    immediate: true,
    metadata: locationMetadata(meta),
  });
}

export function trackLocationPageView(
  opts: LocationAnalyticsMeta & {
    kind: "country" | "state" | "city" | "area";
  },
): void {
  const action =
    opts.kind === "country"
      ? TrackedAction.COUNTRY_PAGE_VIEW
      : opts.kind === "state"
        ? TrackedAction.STATE_PAGE_VIEW
        : opts.kind === "city"
          ? TrackedAction.CITY_PAGE_VIEW
          : TrackedAction.AREA_PAGE_VIEW;
  track(action, {
    immediate: true,
    dedupeScope: `location_page_view:${opts.kind}:${
      opts.area || opts.city || opts.state || opts.country || ""
    }`,
    dedupeTtlMs: 5 * 60_000,
    metadata: locationMetadata(opts),
  });
}

export function trackPadeyaPickImpression(opts: PlacementAnalyticsMeta): void {
  const meta: AnalyticsEventMetadata = {
    ...locationMetadata(opts),
    placement_context: opts.placementContext,
    slot_number: opts.slotNumber,
    event_id: opts.eventId,
  };
  track(TrackedAction.PADEYA_PICK_IMPRESSION, {
    targetEventId: opts.eventId,
    listContext: opts.placementContext,
    dedupeScope: `padeya_pick_impression:${opts.placementContext}:${opts.slotNumber}`,
    dedupeTtlMs: 5 * 60_000,
    metadata: meta,
  });
  if (opts.fromPlacement) {
    track(TrackedAction.FEATURED_PLACEMENT_IMPRESSION, {
      targetEventId: opts.eventId,
      listContext: opts.placementContext,
      dedupeScope: `featured_placement_impression:${opts.placementContext}:${opts.slotNumber}`,
      dedupeTtlMs: 5 * 60_000,
      metadata: meta,
    });
  }
}

export function trackPadeyaPickClick(opts: PlacementAnalyticsMeta): void {
  const meta: AnalyticsEventMetadata = {
    ...locationMetadata(opts),
    placement_context: opts.placementContext,
    slot_number: opts.slotNumber,
    event_id: opts.eventId,
  };
  track(TrackedAction.PADEYA_PICK_CLICK, {
    targetEventId: opts.eventId,
    listContext: opts.placementContext,
    immediate: true,
    metadata: meta,
  });
  if (opts.fromPlacement) {
    track(TrackedAction.FEATURED_PLACEMENT_CLICK, {
      targetEventId: opts.eventId,
      listContext: opts.placementContext,
      immediate: true,
      metadata: meta,
    });
  }
}

export function trackBuyTicketClick(opts: {
  targetEventId: string;
  hostId?: string;
  clickTarget?: string;
}): void {
  track(TrackedAction.CHECKOUT_START_CLICK, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      click_target: opts.clickTarget ?? "buy_ticket",
      page_section: "ticket_cta",
    },
  });
}

export function trackShareClick(opts: {
  targetEventId: string;
  hostId?: string;
  method?: string;
}): void {
  track(TrackedAction.EVENT_SHARE_CLICK, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      click_target: "share",
      page_section: opts.method,
    },
  });
}

export function trackFollowHostClick(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.FOLLOW_HOST_CLICK_FROM_EVENT, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { click_target: "follow_host" },
  });
}

export function trackSaveEventClick(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.SAVE_EVENT_CLICK, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { click_target: "save" },
  });
}

export function trackLegacyClick(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.LEGACY_PAGE_CLICK_FROM_EVENT, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { click_target: "legacy" },
  });
}

export function trackVaultClick(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.VAULT_PREVIEW_CLICK_FROM_EVENT, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { click_target: "vault" },
  });
}

export type VaultAnalyticsMeta = {
  hostId: string;
  vaultItemId?: string | null;
  accessType?: string | null;
  relatedEventId?: string | null;
  lockedState?: boolean | "locked" | "unlocked" | null;
  sourcePage?: string | null;
  listContext?: ListContext | string;
  mediaId?: string | null;
  failureReason?: string | null;
  cardPosition?: number;
  immediate?: boolean;
};

function vaultMetadata(opts: VaultAnalyticsMeta): AnalyticsEventMetadata {
  const locked =
    opts.lockedState === true || opts.lockedState === "locked"
      ? "locked"
      : opts.lockedState === false || opts.lockedState === "unlocked"
        ? "unlocked"
        : undefined;
  return {
    ...(opts.vaultItemId ? { vault_item_id: opts.vaultItemId } : {}),
    ...(opts.accessType ? { access_type: opts.accessType } : {}),
    ...(opts.relatedEventId ? { related_event_id: opts.relatedEventId } : {}),
    ...(locked ? { locked_state: locked } : {}),
    ...(opts.sourcePage ? { source_page: opts.sourcePage } : {}),
    ...(opts.mediaId ? { media_id: opts.mediaId } : {}),
    ...(opts.failureReason ? { failure_reason: opts.failureReason } : {}),
    ...(opts.cardPosition != null ? { card_position: opts.cardPosition } : {}),
  };
}

export function trackVaultPageView(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_PAGE_VIEW, {
    hostId: opts.hostId,
    listContext: opts.listContext as ListContext | undefined,
    immediate: true,
    dedupeTtlMs: 30_000,
    dedupeScope: "vault_page_view",
    metadata: vaultMetadata({ ...opts, sourcePage: opts.sourcePage ?? "vault_catalog" }),
  });
}

export function trackVaultItemImpression(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_ITEM_IMPRESSION, {
    hostId: opts.hostId,
    listContext: opts.listContext as ListContext | undefined,
    dedupeTtlMs: 60_000,
    dedupeScope: `vault_item_impression:${opts.vaultItemId ?? ""}`,
    metadata: vaultMetadata(opts),
  });
}

export function trackVaultItemClick(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_ITEM_CLICK, {
    hostId: opts.hostId,
    listContext: opts.listContext as ListContext | undefined,
    immediate: true,
    metadata: {
      ...vaultMetadata(opts),
      click_target: "vault_item",
    },
  });
}

export function trackVaultItemView(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_ITEM_VIEW, {
    hostId: opts.hostId,
    listContext: opts.listContext as ListContext | undefined,
    immediate: true,
    dedupeTtlMs: 30_000,
    dedupeScope: `vault_item_view:${opts.vaultItemId ?? ""}`,
    metadata: vaultMetadata({
      ...opts,
      sourcePage: opts.sourcePage ?? "vault_item",
    }),
  });
}

export function trackVaultUnlockClick(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_UNLOCK_CLICK, {
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      ...vaultMetadata(opts),
      click_target: "unlock",
    },
  });
}

export function trackVaultUnlockSuccess(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_UNLOCK_SUCCESS, {
    hostId: opts.hostId,
    immediate: true,
    metadata: vaultMetadata({ ...opts, lockedState: "unlocked" }),
  });
}

export function trackVaultUnlockFailed(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_UNLOCK_FAILED, {
    hostId: opts.hostId,
    immediate: true,
    metadata: vaultMetadata(opts),
  });
}

export function trackVaultFollowUnlock(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_FOLLOW_UNLOCK, {
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      ...vaultMetadata(opts),
      click_target: "follow_unlock",
    },
  });
}

export function trackVaultTicketUnlock(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_TICKET_UNLOCK, {
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      ...vaultMetadata(opts),
      click_target: "ticket_unlock",
    },
  });
}

export function trackVaultMediaOpen(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_MEDIA_OPEN, {
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      ...vaultMetadata(opts),
      click_target: "media",
    },
  });
}

export function trackVaultDownloadClick(opts: VaultAnalyticsMeta): void {
  track(TrackedAction.VAULT_DOWNLOAD_CLICK, {
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      ...vaultMetadata(opts),
      click_target: "download",
    },
  });
}

export function trackHostProfileClick(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.HOST_PROFILE_CLICK_FROM_EVENT, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { click_target: "host_profile" },
  });
}

export function trackTicketPanelView(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.TICKET_PANEL_VIEW, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    dedupeScope: "ticket_panel_view",
    dedupeTtlMs: 30 * 60_000,
    metadata: { page_section: "ticket_panel" },
  });
}

/** Event merch — never include payment secrets, buyer PII, spend totals, or private venue copy. */
export function trackMerchSectionViewed(opts: {
  targetEventId: string;
  hostId?: string;
  productCount?: number;
}): void {
  track(TrackedAction.MERCH_SECTION_VIEWED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    dedupeScope: `merch_section_viewed:${opts.targetEventId}`,
    dedupeTtlMs: 30 * 60_000,
    metadata: {
      page_section: "event_merch",
      merch_item_count: opts.productCount,
    },
  });
}

export function trackMerchStorefrontView(opts: {
  hostId: string;
  hostUsername?: string;
  productCount?: number;
}): void {
  track(TrackedAction.MERCH_STOREFRONT_VIEW, {
    hostId: opts.hostId,
    dedupeScope: `merch_storefront_view:${opts.hostId}`,
    dedupeTtlMs: 30 * 60_000,
    metadata: {
      host_username: opts.hostUsername,
      merch_item_count: opts.productCount,
      page_section: "host_merch_storefront",
    },
  });
}

export function trackMerchProductView(opts: {
  targetEventId?: string;
  hostId?: string;
  merchProductId: string;
  merchProductSlug?: string;
  hostUsername?: string;
  eventSlug?: string;
}): void {
  track(TrackedAction.MERCH_PRODUCT_VIEW, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    dedupeScope: `merch_product_view:${opts.merchProductId}`,
    dedupeTtlMs: 10 * 60_000,
    metadata: {
      merch_product_id: opts.merchProductId,
      merch_product_slug: opts.merchProductSlug,
      host_username: opts.hostUsername,
      event_slug: opts.eventSlug,
      page_section: "merch_detail",
    },
  });
}

/** @deprecated Use trackMerchProductView */
export const trackMerchProductViewed = trackMerchProductView;

/** Vault-exclusive merch view — locked_state flag only; never locked Vault content. */
export function trackMerchVaultExclusiveViewed(opts: {
  targetEventId?: string;
  hostId?: string;
  merchProductId: string;
  vaultLocked: boolean;
  hostUsername?: string;
}): void {
  track(TrackedAction.MERCH_VAULT_EXCLUSIVE_VIEWED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    dedupeScope: `merch_vault_exclusive_viewed:${opts.merchProductId}:${opts.vaultLocked ? "locked" : "open"}`,
    dedupeTtlMs: 10 * 60_000,
    metadata: {
      merch_product_id: opts.merchProductId,
      host_username: opts.hostUsername,
      locked_state: opts.vaultLocked,
      page_section: "merch_vault_exclusive",
    },
  });
}

export function trackMerchVariantSelected(opts: {
  targetEventId?: string;
  hostId?: string;
  merchProductId: string;
  merchVariantId: string;
  variantSku?: string;
}): void {
  track(TrackedAction.MERCH_VARIANT_SELECTED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      merch_product_id: opts.merchProductId,
      merch_variant_id: opts.merchVariantId,
      variant_sku: opts.variantSku,
    },
  });
}

export function trackMerchSizeChartOpened(opts: {
  targetEventId?: string;
  hostId?: string;
  merchProductId: string;
}): void {
  track(TrackedAction.MERCH_SIZE_CHART_OPENED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { merch_product_id: opts.merchProductId },
  });
}

export function trackMerchAddedToCart(opts: {
  targetEventId?: string;
  hostId?: string;
  merchProductId: string;
  merchVariantId: string;
  quantity: number;
}): void {
  track(TrackedAction.MERCH_ADDED_TO_CART, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      merch_product_id: opts.merchProductId,
      merch_variant_id: opts.merchVariantId,
      quantity: opts.quantity,
    },
  });
}

/** @deprecated Use trackMerchAddedToCart */
export const trackMerchAddedToCheckout = trackMerchAddedToCart;

export function trackMerchRemovedFromCart(opts: {
  targetEventId?: string;
  hostId?: string;
  merchProductId: string;
  merchVariantId: string;
}): void {
  track(TrackedAction.MERCH_REMOVED_FROM_CART, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      merch_product_id: opts.merchProductId,
      merch_variant_id: opts.merchVariantId,
    },
  });
}

/** @deprecated Use trackMerchRemovedFromCart */
export const trackMerchRemovedFromCheckout = trackMerchRemovedFromCart;

export function trackMerchCheckoutStarted(opts: {
  targetEventId: string;
  hostId?: string;
  orderId?: string;
  merchItemCount: number;
  fulfillmentMethod?: string;
}): void {
  track(TrackedAction.MERCH_CHECKOUT_STARTED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      order_id: opts.orderId,
      merch_item_count: opts.merchItemCount,
      quantity: opts.merchItemCount,
      fulfillment_method: opts.fulfillmentMethod,
    },
  });
}

export function trackMerchDiscountApplied(opts: {
  targetEventId: string;
  hostId?: string;
  discountCode: string;
}): void {
  track(TrackedAction.MERCH_DISCOUNT_APPLIED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      discount_code: opts.discountCode,
      discount_applied: true,
    },
  });
}

export function trackMerchBundleSelected(opts: {
  targetEventId: string;
  hostId?: string;
  bundleId: string;
  quantity: number;
}): void {
  track(TrackedAction.MERCH_BUNDLE_SELECTED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      bundle_id: opts.bundleId,
      quantity: opts.quantity,
    },
  });
}

export function trackMerchQrViewed(opts: {
  targetEventId?: string;
  hostId?: string;
  fulfillmentId?: string;
  merchProductId?: string;
}): void {
  track(TrackedAction.MERCH_QR_VIEWED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    dedupeScope: `merch_qr_viewed:${opts.fulfillmentId || opts.merchProductId || "page"}`,
    dedupeTtlMs: 5 * 60_000,
    metadata: {
      fulfillment_id: opts.fulfillmentId,
      merch_product_id: opts.merchProductId,
      fulfillment_method: "pickup",
      page_section: "merch_qr",
    },
  });
}

export function trackMerchPostEventDropViewed(opts: {
  hostId?: string;
  merchProductId: string;
  hostUsername?: string;
  eventSlug?: string;
}): void {
  track(TrackedAction.MERCH_POST_EVENT_DROP_VIEWED, {
    hostId: opts.hostId,
    dedupeScope: `merch_post_event_drop_viewed:${opts.merchProductId}`,
    dedupeTtlMs: 10 * 60_000,
    metadata: {
      merch_product_id: opts.merchProductId,
      host_username: opts.hostUsername,
      event_slug: opts.eventSlug,
    },
  });
}

export function trackHostMerchRevenueReportViewed(opts?: {
  hostId?: string;
}): void {
  track(TrackedAction.HOST_MERCH_REVENUE_REPORT_VIEWED, {
    hostId: opts?.hostId,
    immediate: true,
    dedupeScope: `host_merch_revenue_report_viewed:${opts?.hostId || "self"}`,
    dedupeTtlMs: 5 * 60_000,
    metadata: { page_section: "host_merch_revenue" },
  });
}

export function trackMerchPickupViewed(opts?: {
  itemCount?: number;
}): void {
  track(TrackedAction.MERCH_PICKUP_VIEWED, {
    immediate: true,
    dedupeScope: "merch_pickup_viewed",
    dedupeTtlMs: 5 * 60_000,
    metadata: {
      page_section: "buyer_merch",
      merch_item_count: opts?.itemCount,
    },
  });
}

export function trackTicketTypeImpression(opts: {
  targetEventId: string;
  hostId?: string;
  ticketTypeId: string;
  ticketTypeName?: string;
  ticketPrice?: number | string;
}): void {
  track(TrackedAction.TICKET_TYPE_IMPRESSION, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    dedupeScope: `ticket_type_impression:${opts.ticketTypeId}`,
    dedupeTtlMs: 10 * 60_000,
    metadata: {
      ticket_type_id: opts.ticketTypeId,
      ticket_type_name: opts.ticketTypeName,
      ticket_price: opts.ticketPrice,
      page_section: "ticket_panel",
    },
  });
}

export function trackTicketTypeSelected(opts: {
  targetEventId: string;
  hostId?: string;
  ticketTypeId: string;
  ticketTypeName?: string;
  ticketPrice?: number | string;
}): void {
  track(TrackedAction.TICKET_TYPE_SELECTED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      ticket_type_id: opts.ticketTypeId,
      ticket_type_name: opts.ticketTypeName,
      ticket_price: opts.ticketPrice,
    },
  });
}

export function trackBuyerTicketsPageView(): void {
  track(TrackedAction.BUYER_TICKETS_PAGE_VIEW, {
    immediate: true,
    dedupeScope: "buyer_tickets_page_view",
    dedupeTtlMs: 5 * 60_000,
    metadata: { page_section: "buyer_tickets" },
  });
}

export function trackTicketTabChanged(opts: { tab: string }): void {
  track(TrackedAction.TICKET_TAB_CHANGED, {
    immediate: true,
    metadata: { tab: opts.tab, page_section: "buyer_tickets" },
  });
}

export function trackTicketGroupExpanded(opts: {
  targetEventId: string;
  expanded: boolean;
}): void {
  track(TrackedAction.TICKET_GROUP_EXPANDED, {
    targetEventId: opts.targetEventId,
    immediate: true,
    metadata: {
      expanded: opts.expanded,
      page_section: "buyer_tickets",
    },
  });
}

export function trackTicketQrClicked(opts: {
  targetEventId: string;
  ticketStatus?: string;
}): void {
  track(TrackedAction.TICKET_QR_CLICKED, {
    targetEventId: opts.targetEventId,
    immediate: true,
    metadata: {
      ticket_status: opts.ticketStatus,
      page_section: "buyer_tickets",
    },
  });
}

export function trackTicketDownloaded(opts: {
  targetEventId: string;
  ticketStatus?: string;
}): void {
  track(TrackedAction.TICKET_DOWNLOADED, {
    targetEventId: opts.targetEventId,
    immediate: true,
    metadata: {
      ticket_status: opts.ticketStatus,
      page_section: "ticket_detail",
      click_target: "download_pdf",
    },
  });
}

export function trackTicketDetailsClicked(opts: {
  targetEventId: string;
  ticketStatus?: string;
}): void {
  track(TrackedAction.TICKET_DETAILS_CLICKED, {
    targetEventId: opts.targetEventId,
    immediate: true,
    metadata: {
      ticket_status: opts.ticketStatus,
      page_section: "buyer_tickets",
    },
  });
}

export function trackTicketEventClicked(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.TICKET_EVENT_CLICKED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { page_section: "buyer_tickets" },
  });
}

export function trackRefundPolicyView(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.REFUND_POLICY_VIEW, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    dedupeScope: "refund_policy_view",
    dedupeTtlMs: 30 * 60_000,
    metadata: { page_section: "policies" },
  });
}

export function trackCheckoutPageView(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.CHECKOUT_PAGE_VIEW, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    dedupeScope: "checkout_page_view",
    dedupeTtlMs: 5 * 60_000,
  });
}

export function trackPromoCodeEntered(opts: {
  targetEventId: string;
  hostId?: string;
  promoCode?: string;
}): void {
  track(TrackedAction.PROMO_CODE_ENTERED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: {
      // Never send full PII; promo codes are intentional product metadata.
      promo_code: opts.promoCode?.trim().slice(0, 64),
    },
  });
}

export function trackPromoCodeResult(opts: {
  targetEventId: string;
  hostId?: string;
  promoCode?: string;
  success: boolean;
  reason?: string;
}): void {
  track(
    opts.success
      ? TrackedAction.PROMO_CODE_APPLIED
      : TrackedAction.PROMO_CODE_FAILED,
    {
      targetEventId: opts.targetEventId,
      hostId: opts.hostId,
      immediate: true,
      metadata: {
        promo_code: opts.promoCode?.trim().slice(0, 64),
        page_section: opts.reason,
      },
    },
  );
}

export function trackCheckoutPaymentStarted(opts: {
  targetEventId: string;
  hostId?: string;
  orderId?: string;
}): void {
  track(TrackedAction.CHECKOUT_PAYMENT_STARTED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    metadata: { order_id: opts.orderId },
  });
}

export function trackCheckoutAbandoned(opts: {
  targetEventId: string;
  hostId?: string;
}): void {
  track(TrackedAction.CHECKOUT_ABANDONED, {
    targetEventId: opts.targetEventId,
    hostId: opts.hostId,
    immediate: true,
    dedupeScope: "checkout_abandoned",
    dedupeTtlMs: 60_000,
  });
}

export function trackHostCardImpression(opts: {
  hostId: string;
  username?: string;
}): void {
  track(TrackedAction.HOST_CARD_IMPRESSION, {
    hostId: opts.hostId,
    dedupeScope: `host_card_impression:${opts.hostId}`,
    dedupeTtlMs: 30 * 60_000,
    listContext: "hosts_marketplace",
    metadata: {
      page_section: "host_card",
      username: opts.username,
    },
  });
}

export function trackHostCardClick(opts: {
  hostId: string;
  username?: string;
  target?: string;
}): void {
  track(TrackedAction.HOST_CARD_CLICK, {
    hostId: opts.hostId,
    immediate: true,
    listContext: "hosts_marketplace",
    metadata: {
      click_target: opts.target || "view_legacy",
      username: opts.username,
    },
  });
}

export function trackLegacyLookupSubmit(opts: { username: string }): void {
  track(TrackedAction.LEGACY_LOOKUP_SUBMIT, {
    immediate: true,
    listContext: "hosts_marketplace",
    metadata: {
      page_section: "legacy_lookup",
      username: opts.username,
    },
  });
}

export function trackHostFollowClick(opts: {
  hostId: string;
  username?: string;
}): void {
  track(TrackedAction.HOST_FOLLOW_CLICK, {
    hostId: opts.hostId,
    immediate: true,
    listContext: "hosts_marketplace",
    metadata: {
      click_target: "follow",
      username: opts.username,
    },
  });
}

export function trackHostFilterUsed(opts: {
  filterType: string;
  value: string;
}): void {
  track(TrackedAction.HOST_FILTER_USED, {
    immediate: true,
    listContext: "hosts_marketplace",
    metadata: {
      page_section: "host_filter",
      filter_type: opts.filterType,
      filter_value: opts.value,
    },
  });
}

export function trackFanDirectoryView(): void {
  track(TrackedAction.FAN_DIRECTORY_VIEW, {
    listContext: "fans_directory",
    dedupeScope: "fan_directory_view",
    dedupeTtlMs: 60_000,
    metadata: { page_section: "fans_directory" },
  });
}

export function trackFanDirectorySearch(opts: { qLength: number }): void {
  track(TrackedAction.FAN_DIRECTORY_SEARCH, {
    immediate: true,
    listContext: "fans_directory",
    metadata: {
      page_section: "fan_directory_search",
      q_length: opts.qLength,
    },
  });
}

export function trackFanDirectoryFilterUsed(opts: {
  filterType: string;
  value: string;
}): void {
  track(TrackedAction.FAN_DIRECTORY_FILTER_USED, {
    immediate: true,
    listContext: "fans_directory",
    metadata: {
      page_section: "fan_directory_filter",
      filter_type: opts.filterType,
      filter_value: opts.value,
    },
  });
}

export function trackFanCardImpression(opts: {
  username: string;
  listContext?: string;
}): void {
  track(TrackedAction.FAN_CARD_IMPRESSION, {
    dedupeScope: `fan_card_impression:${opts.username}`,
    dedupeTtlMs: 30 * 60_000,
    listContext: opts.listContext || "fans_directory",
    metadata: {
      page_section: "fan_card",
      username: opts.username,
    },
  });
}

export function trackFanCardClick(opts: {
  username: string;
  listContext?: string;
}): void {
  track(TrackedAction.FAN_CARD_CLICK, {
    immediate: true,
    listContext: opts.listContext || "fans_directory",
    metadata: {
      click_target: "view_passport",
      username: opts.username,
    },
  });
}

export function trackFanPassportView(opts: { username: string }): void {
  track(TrackedAction.FAN_PASSPORT_VIEW, {
    listContext: "fan_passport",
    dedupeScope: `fan_passport_view:${opts.username}`,
    dedupeTtlMs: 60_000,
    metadata: { username: opts.username },
  });
}

export function trackFanDirectoryOptIn(): void {
  track(TrackedAction.FAN_DIRECTORY_OPT_IN, {
    immediate: true,
    listContext: "passport_settings",
    metadata: { page_section: "public_discovery" },
  });
}

export function trackFanDirectoryOptOut(): void {
  track(TrackedAction.FAN_DIRECTORY_OPT_OUT, {
    immediate: true,
    listContext: "passport_settings",
    metadata: { page_section: "public_discovery" },
  });
}

/** Fan Connect — never include private attendance, venues, tickets, spend, PII, Vault. */
export function trackFanConnectPageView(opts?: { path?: string }): void {
  const path =
    opts?.path ??
    (typeof window !== "undefined" ? window.location.pathname : "/connect");
  track(TrackedAction.FAN_CONNECT_PAGE_VIEW, {
    immediate: true,
    dedupeScope: `fan_connect_page_view:${path}`,
    dedupeTtlMs: 60_000,
    listContext: "fan_connect",
    metadata: { page_section: "fan_connect", path },
  });
}

export function trackFanConnectSettingsUpdated(opts?: {
  fanConnectEnabled?: boolean;
  requestPolicy?: string;
}): void {
  track(TrackedAction.FAN_CONNECT_SETTINGS_UPDATED, {
    immediate: true,
    listContext: "fan_connect_settings",
    metadata: {
      page_section: "fan_connect_settings",
      fan_connect_enabled: opts?.fanConnectEnabled,
      request_policy: opts?.requestPolicy,
    },
  });
}

export function trackFanConnectSuggestionImpression(opts: {
  username: string;
  listContext?: string;
  scoreBand?: string | null;
  ctaState?: string | null;
}): void {
  track(TrackedAction.FAN_CONNECT_SUGGESTION_IMPRESSION, {
    dedupeScope: `fan_connect_suggestion_impression:${opts.username}`,
    dedupeTtlMs: 30 * 60_000,
    listContext: opts.listContext || "fan_connect_suggestions",
    metadata: {
      page_section: "fan_connect_suggestion",
      username: opts.username,
      score_band: opts.scoreBand || undefined,
      cta_state: opts.ctaState || undefined,
    },
  });
}

export function trackFanConnectSuggestionClicked(opts: {
  username: string;
  listContext?: string;
  clickTarget?: string;
  scoreBand?: string | null;
}): void {
  track(TrackedAction.FAN_CONNECT_SUGGESTION_CLICKED, {
    immediate: true,
    listContext: opts.listContext || "fan_connect_suggestions",
    metadata: {
      page_section: "fan_connect_suggestion",
      username: opts.username,
      click_target: opts.clickTarget ?? "connect",
      score_band: opts.scoreBand || undefined,
    },
  });
}

export function trackMessageCtaClicked(opts: {
  context: string;
  hostUsername?: string;
}): void {
  track(TrackedAction.MESSAGE_CTA_CLICKED, {
    immediate: true,
    metadata: {
      page_section: opts.context,
      username: opts.hostUsername,
      click_target: "message_host",
    },
  });
}

export function trackHostMessageFanClicked(): void {
  track(TrackedAction.HOST_MESSAGE_FAN_CLICKED, {
    immediate: true,
    metadata: { click_target: "message_fan" },
  });
}

export const LIST_CONTEXT = {
  homepageFeatured: "homepage_featured" as const,
  eventsGrid: "events_grid" as const,
  categoryPage: "category_page" as const,
  cityPage: "city_page" as const,
  legacyUpcoming: "legacy_upcoming" as const,
  searchResults: "search_results" as const,
  sponsorRelated: "sponsor_related" as const,
  demoPage: "demo_page" as const,
  relatedEvents: "related_events" as const,
  hostsMarketplace: "hosts_marketplace" as const,
};

export const IMPRESSION_THRESHOLD = {
  ratio: IMPRESSION_VISIBLE_RATIO,
  dwellMs: IMPRESSION_DWELL_MS,
};

export { TrackedAction };
