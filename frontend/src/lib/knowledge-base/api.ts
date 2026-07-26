/** Knowledge Base / Help Center API types + client helpers. */

import { cache } from "react";

import { apiRequest } from "@/lib/api";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";

export type HelpCategory = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  group_key: string;
  sort_order: number;
  icon_key?: string | null;
  article_count: number;
};

export type HelpTag = {
  id: string;
  name: string;
  slug: string;
};

export type HelpArticleListItem = {
  id: string;
  title: string;
  slug: string;
  excerpt?: string | null;
  content_type: string;
  difficulty: string;
  audiences: string[];
  cover_url?: string | null;
  video_url?: string | null;
  video_provider?: string | null;
  video_thumbnail_url?: string | null;
  status: string;
  is_featured: boolean;
  reading_time_minutes: number;
  helpful_count: number;
  not_helpful_count: number;
  view_count: number;
  published_at?: string | null;
  updated_at?: string | null;
  category?: HelpCategory | null;
  tags?: HelpTag[];
};

export type HelpArticle = HelpArticleListItem & {
  body: string;
  body_html: string;
  video_embed_url?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  related?: HelpArticleListItem[];
  related_article_ids?: string[];
  scheduled_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  archived_at?: string | null;
  created_at?: string | null;
  featured_sort?: number;
};

export type ArticlePayload = {
  title: string;
  slug?: string | null;
  excerpt?: string | null;
  body?: string;
  content_type?: string;
  difficulty?: string;
  audiences?: string[];
  cover_url?: string | null;
  video_url?: string | null;
  category_id?: string | null;
  tag_slugs?: string[];
  is_featured?: boolean;
  featured_sort?: number;
  seo_title?: string | null;
  seo_description?: string | null;
  related_article_ids?: string[];
  status?: string;
  scheduled_at?: string | null;
};

function apiRoot(): string {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  const origin = base || "http://127.0.0.1:8000";
  return `${origin}${prefix}`;
}

const HELP_FETCH = {
  next: { revalidate: 300, tags: ["help"] as string[] },
};

export async function fetchHelpArticles(params?: {
  category?: string;
  tag?: string;
  audience?: string;
  featured?: boolean;
  popular?: boolean;
  q?: string;
  limit?: number;
}): Promise<HelpArticleListItem[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.tag) qs.set("tag", params.tag);
  if (params?.audience) qs.set("audience", params.audience);
  if (params?.featured) qs.set("featured", "true");
  if (params?.popular) qs.set("popular", "true");
  if (params?.q) qs.set("q", params.q);
  if (params?.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiRequest<HelpArticleListItem[]>(`/help/articles${q ? `?${q}` : ""}`, {
    auth: false,
  });
}

export async function fetchHelpArticle(slug: string): Promise<HelpArticle> {
  return apiRequest<HelpArticle>(`/help/articles/${encodeURIComponent(slug)}`, {
    auth: false,
  });
}

export async function fetchHelpCategories(): Promise<HelpCategory[]> {
  return apiRequest<HelpCategory[]>("/help/categories", { auth: false });
}

export async function submitHelpFeedback(
  articleId: string,
  body: { is_helpful: boolean; comment?: string },
) {
  return apiRequest<{
    article_id: string;
    helpful_count: number;
    not_helpful_count: number;
  }>(`/help/articles/${articleId}/feedback`, {
    method: "POST",
    auth: false,
    body: JSON.stringify(body),
  });
}

export async function fetchAdminHelpArticles(params?: {
  status?: string;
  q?: string;
}): Promise<HelpArticle[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  const q = qs.toString();
  return apiRequest<HelpArticle[]>(
    `/admin/knowledge-base/articles${q ? `?${q}` : ""}`,
  );
}

export async function fetchAdminHelpArticle(id: string): Promise<HelpArticle> {
  return apiRequest<HelpArticle>(`/admin/knowledge-base/articles/${id}`);
}

export async function createAdminHelpArticle(
  body: ArticlePayload,
): Promise<HelpArticle> {
  return apiRequest<HelpArticle>("/admin/knowledge-base/articles", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateAdminHelpArticle(
  id: string,
  body: Partial<ArticlePayload>,
): Promise<HelpArticle> {
  return apiRequest<HelpArticle>(`/admin/knowledge-base/articles/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function publishAdminHelpArticle(id: string): Promise<HelpArticle> {
  return apiRequest<HelpArticle>(
    `/admin/knowledge-base/articles/${id}/publish`,
    { method: "POST" },
  );
}

export async function archiveAdminHelpArticle(id: string): Promise<HelpArticle> {
  return apiRequest<HelpArticle>(
    `/admin/knowledge-base/articles/${id}/archive`,
    { method: "POST" },
  );
}

export async function deleteAdminHelpArticle(id: string): Promise<void> {
  await apiRequest<void>(`/admin/knowledge-base/articles/${id}`, {
    method: "DELETE",
  });
}

export async function fetchAdminHelpCategories(
  includeArchived = false,
): Promise<HelpCategory[]> {
  const qs = includeArchived ? "?include_archived=true" : "";
  return apiRequest<HelpCategory[]>(`/admin/knowledge-base/categories${qs}`);
}

export async function createAdminHelpCategory(body: {
  name: string;
  slug?: string;
  description?: string;
  group_key?: string;
  sort_order?: number;
  icon_key?: string;
}): Promise<HelpCategory> {
  return apiRequest<HelpCategory>("/admin/knowledge-base/categories", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateAdminHelpCategory(
  id: string,
  body: Partial<{
    name: string;
    slug: string;
    description: string;
    group_key: string;
    sort_order: number;
    icon_key: string;
  }>,
): Promise<HelpCategory> {
  return apiRequest<HelpCategory>(`/admin/knowledge-base/categories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function seedAdminHelp() {
  return apiRequest<Record<string, unknown>>("/admin/knowledge-base/seed", {
    method: "POST",
  });
}

export async function fetchHelpArticlesServer(params?: {
  category?: string;
  audience?: string;
  featured?: boolean;
  popular?: boolean;
  q?: string;
  limit?: number;
}): Promise<HelpArticleListItem[]> {
  try {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.audience) qs.set("audience", params.audience);
    if (params?.featured) qs.set("featured", "true");
    if (params?.popular) qs.set("popular", "true");
    if (params?.q) qs.set("q", params.q);
    qs.set("limit", String(params?.limit ?? 50));
    const res = await fetch(`${apiRoot()}/help/articles?${qs}`, HELP_FETCH);
    if (!res.ok) return [];
    return (await res.json()) as HelpArticleListItem[];
  } catch {
    return [];
  }
}

export const fetchHelpArticleServer = cache(async (
  slug: string,
): Promise<HelpArticle | null> => {
  try {
    const res = await fetch(
      `${apiRoot()}/help/articles/${encodeURIComponent(slug)}`,
      HELP_FETCH,
    );
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return (await res.json()) as HelpArticle;
  } catch {
    return null;
  }
});

export async function fetchHelpCategoriesServer(): Promise<HelpCategory[]> {
  try {
    const res = await fetch(`${apiRoot()}/help/categories`, HELP_FETCH);
    if (!res.ok) return [];
    return (await res.json()) as HelpCategory[];
  } catch {
    return [];
  }
}

export async function fetchHelpCategoryServer(
  slug: string,
): Promise<HelpCategory | null> {
  try {
    const res = await fetch(
      `${apiRoot()}/help/categories/${encodeURIComponent(slug)}`,
      HELP_FETCH,
    );
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return (await res.json()) as HelpCategory;
  } catch {
    return null;
  }
}

export const HELP_GROUP_LABELS: Record<string, string> = {
  fan: "Fan Help",
  host: "Host Help",
  sponsor: "Sponsor Help",
  ambassador: "Ambassador Help",
  account: "Account & Safety",
  payments: "Payments & Policies",
  admin: "Admin Help",
  general: "General",
  visitor: "Visitor guides",
};
