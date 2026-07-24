import type { MetadataRoute } from "next";

import { fetchBlogPostsServer } from "@/lib/blog-api";
import {
  fetchHelpArticlesServer,
  fetchHelpCategoriesServer,
} from "@/lib/knowledge-base/api";
import { siteOrigin } from "@/lib/seo/site";
import {
  SPONSORSHIP_HOSTS_PATH,
  SPONSORSHIP_MARKETPLACE_PATH,
} from "@/lib/sponsor-marketplace-paths";
import { filterListedEventsForSitemap } from "@/lib/seo/sitemap-filter";

const API =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000/api/v1";

type PublicEvent = {
  slug: string;
  city?: string | null;
  category?: { slug: string } | null;
  visibility?: string;
  updated_at?: string;
  published_at?: string | null;
};

type Category = { slug: string; is_active?: boolean };

type TaxonomyLocation = {
  kind: string;
  slug: string;
  is_active?: boolean;
};

function slugify(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

async function safeJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API}${path}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = siteOrigin();
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [
    { url: `${origin}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${origin}/events`, lastModified: now, changeFrequency: "hourly", priority: 0.9 },
    {
      url: `${origin}/events/location`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.75,
    },
    { url: `${origin}/hosts`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${origin}${SPONSORSHIP_MARKETPLACE_PATH}`, lastModified: now, changeFrequency: "weekly", priority: 0.6 },
    { url: `${origin}${SPONSORSHIP_HOSTS_PATH}`, lastModified: now, changeFrequency: "weekly", priority: 0.6 },
    { url: `${origin}/events/this-weekend`, lastModified: now, changeFrequency: "daily", priority: 0.7 },
    { url: `${origin}/events/free`, lastModified: now, changeFrequency: "daily", priority: 0.6 },
    { url: `${origin}/events/vip`, lastModified: now, changeFrequency: "daily", priority: 0.6 },
    { url: `${origin}/blog`, lastModified: now, changeFrequency: "daily", priority: 0.75 },
    { url: `${origin}/help`, lastModified: now, changeFrequency: "daily", priority: 0.8 },
    { url: `${origin}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${origin}/for-hosts`, lastModified: now, changeFrequency: "monthly", priority: 0.75 },
    { url: `${origin}/for-fans`, lastModified: now, changeFrequency: "monthly", priority: 0.75 },
    { url: `${origin}/merch-guide`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${origin}/merch`, lastModified: now, changeFrequency: "daily", priority: 0.85 },
    { url: `${origin}/merch/drops`, lastModified: now, changeFrequency: "daily", priority: 0.75 },
    { url: `${origin}/merch/vault`, lastModified: now, changeFrequency: "daily", priority: 0.7 },
    { url: `${origin}/pricing`, lastModified: now, changeFrequency: "monthly", priority: 0.55 },
    { url: `${origin}/faq`, lastModified: now, changeFrequency: "weekly", priority: 0.55 },
    { url: `${origin}/contact`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${origin}/support`, lastModified: now, changeFrequency: "weekly", priority: 0.6 },
    { url: `${origin}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${origin}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${origin}/cookies`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${origin}/refund-policy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${origin}/ticket-policy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${origin}/community-guidelines`, lastModified: now, changeFrequency: "yearly", priority: 0.35 },
    { url: `${origin}/safety`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    { url: `${origin}/report`, lastModified: now, changeFrequency: "monthly", priority: 0.35 },
    { url: `${origin}/accessibility`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${origin}/events/today`, lastModified: now, changeFrequency: "hourly", priority: 0.7 },
    { url: `${origin}/events/search`, lastModified: now, changeFrequency: "daily", priority: 0.65 },
  ];

  const [events, categories, locations, blogPosts, helpArticles, helpCategories, merchList] =
    await Promise.all([
      safeJson<PublicEvent[]>("/events"),
      safeJson<Category[]>("/events/categories"),
      safeJson<TaxonomyLocation[]>("/taxonomy/locations"),
      fetchBlogPostsServer({ limit: 100 }),
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
    ]);

  for (const post of blogPosts) {
    if (post.status !== "published") continue;
    entries.push({
      url: `${origin}/blog/${post.slug}`,
      lastModified: post.updated_at
        ? new Date(post.updated_at)
        : post.published_at
          ? new Date(post.published_at)
          : now,
      changeFrequency: "weekly",
      priority: 0.65,
    });
  }

  for (const article of helpArticles) {
    if (article.status !== "published") continue;
    entries.push({
      url: `${origin}/help/articles/${article.slug}`,
      lastModified: article.updated_at
        ? new Date(article.updated_at)
        : article.published_at
          ? new Date(article.published_at)
          : now,
      changeFrequency: "weekly",
      priority: 0.7,
    });
  }

  for (const cat of helpCategories) {
    entries.push({
      url: `${origin}/help/${cat.slug}`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.6,
    });
  }

  const listed = filterListedEventsForSitemap(events ?? []);

  const cities = new Set<string>();
  const cityCategory = new Set<string>();

  for (const event of listed) {
    entries.push({
      url: `${origin}/events/${event.slug}`,
      lastModified: event.updated_at
        ? new Date(event.updated_at)
        : event.published_at
          ? new Date(event.published_at)
          : now,
      changeFrequency: "daily",
      priority: 0.8,
    });
    if (event.city) cities.add(slugify(event.city));
    if (event.category?.slug && event.city) {
      cityCategory.add(`${slugify(event.city)}::${event.category.slug}`);
    }
  }

  for (const cat of categories ?? []) {
    entries.push({
      url: `${origin}/events/c/${cat.slug}`,
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
    if (loc.is_active === false) continue;
    if (!["country", "state", "city", "area"].includes(loc.kind)) continue;
    entries.push({
      url: `${origin}/events/${loc.kind}/${loc.slug}`,
      lastModified: now,
      changeFrequency: "daily",
      priority: hubPriority[loc.kind] ?? 0.65,
    });
  }

  for (const city of cities) {
    const path = `${origin}/events/city/${city}`;
    if (!entries.some((e) => e.url === path)) {
      entries.push({
        url: path,
        lastModified: now,
        changeFrequency: "daily",
        priority: 0.7,
      });
    }
  }

  for (const key of cityCategory) {
    const [city, cat] = key.split("::");
    if (city && cat) {
      entries.push({
        url: `${origin}/events/city/${city}/${cat}`,
        lastModified: now,
        changeFrequency: "daily",
        priority: 0.65,
      });
    }
  }

  for (const item of merchList?.items ?? []) {
    if (item.indexable === false) continue;
    const path =
      item.marketplace_path?.split("?")[0] ||
      (item.host_slug
        ? `/merch/${item.slug}?h=${item.host_slug}`
        : `/merch/${item.slug}`);
    const urlPath = path.startsWith("http")
      ? path
      : `${origin}${path.startsWith("/") ? path : `/${path}`}`;
    // Prefer clean slug URLs without query for sitemap when host disambiguator present.
    const cleanUrl = item.host_slug
      ? `${origin}/merch/${item.slug}`
      : urlPath.includes("?")
        ? urlPath.split("?")[0]
        : urlPath;
    if (!entries.some((e) => e.url === cleanUrl)) {
      entries.push({
        url: cleanUrl,
        lastModified: item.updated_at ? new Date(item.updated_at) : now,
        changeFrequency: "weekly",
        priority: 0.55,
      });
    }
  }

  return entries;
}
