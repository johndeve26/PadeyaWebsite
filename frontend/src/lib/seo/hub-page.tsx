import type { SeoEnvInput } from "@/lib/seo/env-policy";
import { buildPageMetadata, siteOrigin } from "@/lib/seo/site";
import {
  breadcrumbJsonLd,
  collectionPageJsonLd,
  JsonLdScript,
} from "@/lib/seo/jsonld";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = process.env.NEXT_PUBLIC_API_PREFIX ?? "/api/v1";

export type TaxonomyTermSeo = {
  name: string;
  slug: string;
  description?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  is_active?: boolean;
  seo_index_mode?: string | null;
  intro_content?: string | null;
};

async function safeJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${API_PREFIX}${path}`, {
      next: { revalidate: 120 },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchTaxonomyCategoryBySlug(
  slug: string,
): Promise<TaxonomyTermSeo | null> {
  const rows = await safeJson<TaxonomyTermSeo[]>("/taxonomy/categories");
  return rows?.find((r) => r.slug === slug) ?? null;
}

export async function fetchTaxonomyLocationBySlug(
  slug: string,
  kind: string = "city",
): Promise<TaxonomyTermSeo | null> {
  const detail = await safeJson<{
    location: TaxonomyTermSeo & { kind?: string };
  }>(`/taxonomy/locations/${encodeURIComponent(kind)}/${encodeURIComponent(slug)}`);
  return detail?.location ?? null;
}

export async function fetchTaxonomyLocationDetailSeo(
  kind: string,
  slug: string,
): Promise<{
  location: TaxonomyTermSeo & { kind: string; slug: string; name: string };
  ancestors: { kind: string; slug: string; name: string }[];
  children: { kind: string; slug: string; name: string }[];
  siblings?: { kind: string; slug: string; name: string }[];
} | null> {
  return safeJson(
    `/taxonomy/locations/${encodeURIComponent(kind)}/${encodeURIComponent(slug)}`,
  );
}

export function hubPageMetadata(opts: {
  title: string;
  description: string;
  path: string;
  seoTitle?: string | null;
  seoDescription?: string | null;
  noIndex?: boolean;
  /** Soft public noindex (facets/thin hubs) — keep follow when true. */
  noIndexFollow?: boolean;
  /** When set, canonical points here instead of `path` (e.g. /events/search → /events). */
  canonicalPath?: string;
  env?: SeoEnvInput;
}) {
  return buildPageMetadata({
    title: opts.seoTitle || opts.title,
    description: opts.seoDescription || opts.description,
    path: opts.canonicalPath || opts.path,
    noIndex: opts.noIndex,
    noIndexFollow: opts.noIndexFollow,
    env: opts.env,
  });
}

export function HubJsonLd({
  name,
  description,
  path,
  crumbs,
}: {
  name: string;
  description: string;
  path: string;
  crumbs: BreadcrumbItem[];
}) {
  const origin = siteOrigin();
  return (
    <>
      <JsonLdScript
        data={collectionPageJsonLd({ name, description, path, origin })}
      />
      <JsonLdScript data={breadcrumbJsonLd(crumbs, origin)} />
    </>
  );
}
