import type { MetadataRoute } from "next";

import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import {
  fetchBlogAuthorsServer,
  fetchBlogCategoriesServer,
  fetchBlogPostsServer,
  fetchBlogTagsServer,
} from "@/lib/blog-api";
import {
  fetchHelpArticlesServer,
  fetchHelpCategoriesServer,
} from "@/lib/knowledge-base/api";
import { getCanonicalSiteOrigin } from "@/lib/seo/site";
import {
  collectNonEmptyBlogHubSlugs,
  filterFansForSitemap,
  filterHostsForSitemap,
  filterListedEventsForSitemap,
  filterMerchForSitemap,
  filterSponsorsForSitemap,
  isPublishedBlogPost,
  sitemapLastModified,
} from "@/lib/seo/sitemap-filter";
import {
  buildHubInventoryFromEvents,
  isCityCategoryInSitemap,
  isLocationInSitemap,
} from "@/lib/seo/hub-eligibility";
import {
  SPONSORSHIP_HOSTS_PATH,
  SPONSORSHIP_MARKETPLACE_PATH,
} from "@/lib/sponsor-marketplace-paths";

function apiRoot(): string {
  const base = getApiBaseUrl() || "http://127.0.0.1:8000";
  return `${base}${getApiPrefix()}`;
}

type PublicEvent = {
  slug: string;
  city?: string | null;
  category?: { slug: string } | null;
  visibility?: string;
  updated_at?: string;
  published_at?: string | null;
  location?: {
    kind?: string | null;
    slug?: string | null;
    ancestors?: Array<{ kind?: string | null; slug?: string | null }> | null;
  } | null;
};

type Category = { slug: string; is_active?: boolean };

type TaxonomyLocation = {
  kind: string;
  slug: string;
  is_active?: boolean;
  seo_index_mode?: string | null;
};

type DiscoverHost = { username: string };
type FanDirectoryCard = { username: string };
type FanDirectoryList = {
  items: FanDirectoryCard[];
  page: number;
  limit: number;
  total: number;
};
type SponsorDirectoryCard = { slug: string; verified?: boolean };

async function safeJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${apiRoot()}${path}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/** Paginate public Fan directory (max 48/page) — public+directory-eligible only. */
async function fetchAllDirectoryFans(): Promise<FanDirectoryCard[]> {
  const out: FanDirectoryCard[] = [];
  const limit = 48;
  let page = 1;
  let total = Infinity;

  while (out.length < total && page <= 50) {
    const data = await safeJson<FanDirectoryList>(
      `/fans?page=${page}&limit=${limit}&sort=recently_active`,
    );
    if (!data?.items?.length) break;
    out.push(...data.items);
    total = typeof data.total === "number" ? data.total : out.length;
    if (data.items.length < limit) break;
    page += 1;
  }

  return out;
}

function pushEntry(
  entries: MetadataRoute.Sitemap,
  url: string,
  opts: {
    lastModified?: Date;
    changeFrequency?: MetadataRoute.Sitemap[number]["changeFrequency"];
    priority?: number;
  },
) {
  const entry: MetadataRoute.Sitemap[number] = {
    url,
    changeFrequency: opts.changeFrequency,
    priority: opts.priority,
  };
  if (opts.lastModified) entry.lastModified = opts.lastModified;
  entries.push(entry);
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = getCanonicalSiteOrigin();
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [];

  // Static / marketing surfaces — lastModified = generation time is OK (no entity clock).
  const staticPages: Array<{
    path: string;
    changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
    priority: number;
  }> = [
    { path: "/", changeFrequency: "daily", priority: 1 },
    { path: "/events", changeFrequency: "hourly", priority: 0.9 },
    { path: "/events/location", changeFrequency: "daily", priority: 0.75 },
    { path: "/hosts", changeFrequency: "weekly", priority: 0.7 },
    { path: "/fans", changeFrequency: "weekly", priority: 0.65 },
    {
      path: SPONSORSHIP_MARKETPLACE_PATH,
      changeFrequency: "weekly",
      priority: 0.6,
    },
    { path: SPONSORSHIP_HOSTS_PATH, changeFrequency: "weekly", priority: 0.6 },
    { path: "/events/this-weekend", changeFrequency: "daily", priority: 0.7 },
    { path: "/events/free", changeFrequency: "daily", priority: 0.6 },
    { path: "/events/vip", changeFrequency: "daily", priority: 0.6 },
    { path: "/events/today", changeFrequency: "hourly", priority: 0.7 },
    { path: "/blog", changeFrequency: "daily", priority: 0.75 },
    { path: "/help", changeFrequency: "daily", priority: 0.8 },
    { path: "/about", changeFrequency: "monthly", priority: 0.5 },
    { path: "/for-hosts", changeFrequency: "monthly", priority: 0.75 },
    { path: "/for-fans", changeFrequency: "monthly", priority: 0.75 },
    { path: "/merch-guide", changeFrequency: "monthly", priority: 0.7 },
    { path: "/merch", changeFrequency: "daily", priority: 0.85 },
    { path: "/merch/drops", changeFrequency: "daily", priority: 0.75 },
    { path: "/merch/vault", changeFrequency: "daily", priority: 0.7 },
    { path: "/pricing", changeFrequency: "monthly", priority: 0.55 },
    { path: "/faq", changeFrequency: "weekly", priority: 0.55 },
    { path: "/contact", changeFrequency: "monthly", priority: 0.5 },
    { path: "/support", changeFrequency: "weekly", priority: 0.6 },
    { path: "/ambassadors", changeFrequency: "monthly", priority: 0.55 },
    { path: "/ambassadors/events", changeFrequency: "weekly", priority: 0.5 },
    {
      path: "/ambassadors/how-it-works",
      changeFrequency: "monthly",
      priority: 0.5,
    },
    { path: "/terms", changeFrequency: "yearly", priority: 0.3 },
    { path: "/privacy", changeFrequency: "yearly", priority: 0.3 },
    { path: "/cookies", changeFrequency: "yearly", priority: 0.3 },
    { path: "/refund-policy", changeFrequency: "yearly", priority: 0.3 },
    { path: "/ticket-policy", changeFrequency: "yearly", priority: 0.3 },
    {
      path: "/community-guidelines",
      changeFrequency: "yearly",
      priority: 0.35,
    },
    { path: "/safety", changeFrequency: "monthly", priority: 0.4 },
    { path: "/report", changeFrequency: "monthly", priority: 0.35 },
    { path: "/accessibility", changeFrequency: "yearly", priority: 0.3 },
  ];

  for (const page of staticPages) {
    pushEntry(entries, `${origin}${page.path}`, {
      lastModified: now,
      changeFrequency: page.changeFrequency,
      priority: page.priority,
    });
  }

  const [
    events,
    categories,
    locations,
    blogPosts,
    blogCategories,
    blogTags,
    blogAuthors,
    helpArticles,
    helpCategories,
    merchList,
    discoverHosts,
    directoryFans,
    sponsors,
  ] = await Promise.all([
    safeJson<PublicEvent[]>("/events"),
    safeJson<Category[]>("/events/categories"),
    safeJson<TaxonomyLocation[]>("/taxonomy/locations"),
    fetchBlogPostsServer({ limit: 100 }),
    fetchBlogCategoriesServer(),
    fetchBlogTagsServer(),
    fetchBlogAuthorsServer(),
    fetchHelpArticlesServer({ limit: 100 }),
    fetchHelpCategoriesServer(),
    safeJson<{
      items?: Array<{
        slug: string;
        host_slug?: string | null;
        marketplace_path?: string | null;
        indexable?: boolean;
        updated_at?: string;
      }>;
    }>("/merch?limit=100&sort=newest"),
    safeJson<DiscoverHost[]>("/legacy/discover/hosts"),
    fetchAllDirectoryFans(),
    safeJson<SponsorDirectoryCard[]>("/sponsors/public/directory"),
  ]);

  for (const post of blogPosts) {
    if (!isPublishedBlogPost(post)) continue;
    pushEntry(entries, `${origin}/blog/${post.slug}`, {
      lastModified: sitemapLastModified(post.updated_at, post.published_at),
      changeFrequency: "weekly",
      priority: 0.65,
    });
  }

  const blogHubs = collectNonEmptyBlogHubSlugs(blogPosts);
  for (const cat of blogCategories) {
    if (!blogHubs.categories.has(cat.slug)) continue;
    pushEntry(entries, `${origin}/blog/category/${encodeURIComponent(cat.slug)}`, {
      changeFrequency: "weekly",
      priority: 0.55,
    });
  }
  for (const tag of blogTags) {
    if (!blogHubs.tags.has(tag.slug)) continue;
    pushEntry(entries, `${origin}/blog/tag/${encodeURIComponent(tag.slug)}`, {
      changeFrequency: "weekly",
      priority: 0.5,
    });
  }
  for (const author of blogAuthors) {
    if (!blogHubs.authors.has(author.slug)) continue;
    pushEntry(entries, `${origin}/blog/author/${encodeURIComponent(author.slug)}`, {
      changeFrequency: "weekly",
      priority: 0.5,
    });
  }

  for (const article of helpArticles) {
    if (article.status !== "published") continue;
    pushEntry(entries, `${origin}/help/articles/${article.slug}`, {
      lastModified: sitemapLastModified(article.updated_at, article.published_at),
      changeFrequency: "weekly",
      priority: 0.7,
    });
  }

  for (const cat of helpCategories) {
    pushEntry(entries, `${origin}/help/${cat.slug}`, {
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.6,
    });
  }

  const listed = filterListedEventsForSitemap(events ?? []);
  const { locationCounts, cityCategoryCounts } =
    buildHubInventoryFromEvents(listed);

  const cityBySlug = new Map(
    (locations ?? [])
      .filter((l) => l.kind === "city")
      .map((l) => [l.slug, l] as const),
  );

  for (const event of listed) {
    pushEntry(entries, `${origin}/events/${event.slug}`, {
      lastModified: sitemapLastModified(event.updated_at, event.published_at),
      changeFrequency: "daily",
      priority: 0.8,
    });
  }

  for (const cat of categories ?? []) {
    pushEntry(entries, `${origin}/events/c/${cat.slug}`, {
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.7,
    });
  }

  const hubPriority: Record<string, number> = {
    country: 0.78,
    state: 0.74,
    city: 0.72,
    area: 0.68,
  };

  for (const loc of locations ?? []) {
    if (!["country", "state", "city", "area"].includes(loc.kind)) continue;
    if (!isLocationInSitemap(loc, locationCounts)) continue;
    pushEntry(entries, `${origin}/events/${loc.kind}/${loc.slug}`, {
      lastModified: now,
      changeFrequency: "daily",
      priority: hubPriority[loc.kind] ?? 0.65,
    });
  }

  // City hubs derived from event.city text when taxonomy row missing but inventory enough.
  for (const [key, count] of locationCounts) {
    if (!key.startsWith("city::")) continue;
    const citySlug = key.slice("city::".length);
    const path = `${origin}/events/city/${citySlug}`;
    if (entries.some((e) => e.url === path)) continue;
    if (
      !isLocationInSitemap(
        {
          kind: "city",
          slug: citySlug,
          is_active: true,
          seo_index_mode: cityBySlug.get(citySlug)?.seo_index_mode,
        },
        locationCounts,
      )
    ) {
      continue;
    }
    // silence unused when count always used via helper
    void count;
    pushEntry(entries, path, {
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.7,
    });
  }

  for (const [key, count] of cityCategoryCounts) {
    const [city, cat] = key.split("::");
    if (!city || !cat) continue;
    if (
      !isCityCategoryInSitemap(city, cat, cityCategoryCounts, cityBySlug.get(city))
    ) {
      continue;
    }
    void count;
    pushEntry(entries, `${origin}/events/city/${city}/${cat}`, {
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.65,
    });
  }

  for (const item of filterMerchForSitemap(merchList?.items ?? [])) {
    const cleanUrl = `${origin}/merch/${item.slug}`;
    if (!entries.some((e) => e.url === cleanUrl)) {
      pushEntry(entries, cleanUrl, {
        lastModified: sitemapLastModified(item.updated_at),
        changeFrequency: "weekly",
        priority: 0.55,
      });
    }
  }

  // Host Legacy — public discover API (active hosts with listed marketplace events).
  for (const host of filterHostsForSitemap(discoverHosts ?? [])) {
    pushEntry(entries, `${origin}/u/${encodeURIComponent(host.username.trim())}`, {
      changeFrequency: "weekly",
      priority: 0.7,
    });
  }

  // Fan Passports — public directory API only (public + appear_in_directory + not hidden).
  for (const fan of filterFansForSitemap(directoryFans)) {
    pushEntry(entries, `${origin}/f/${encodeURIComponent(fan.username.trim())}`, {
      changeFrequency: "weekly",
      priority: 0.55,
    });
  }

  // Sponsors — public directory (active + public visibility + verified).
  for (const sponsor of filterSponsorsForSitemap(sponsors ?? [])) {
    pushEntry(
      entries,
      `${origin}/sponsors/${encodeURIComponent(sponsor.slug.trim())}`,
      {
        changeFrequency: "weekly",
        priority: 0.6,
      },
    );
  }

  return entries;
}
