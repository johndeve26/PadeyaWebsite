/** Blog API types + client helpers. */

import { cache } from "react";

import { apiRequest } from "@/lib/api";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";

export type BlogCategory = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
};

export type BlogTag = {
  id: string;
  name: string;
  slug: string;
};

export type BlogAuthor = {
  id: string;
  display_name: string;
  slug: string;
  bio?: string | null;
  avatar_url?: string | null;
  role_title?: string | null;
};

export type BlogPostListItem = {
  id: string;
  title: string;
  slug: string;
  excerpt?: string | null;
  cover_url?: string | null;
  status: string;
  is_featured: boolean;
  reading_time_minutes: number;
  published_at?: string | null;
  scheduled_at?: string | null;
  updated_at?: string | null;
  category?: BlogCategory | null;
  author?: BlogAuthor | null;
  tags?: BlogTag[];
};

export type BlogPost = BlogPostListItem & {
  body: string;
  body_html: string;
  seo_title?: string | null;
  seo_description?: string | null;
  canonical_url?: string | null;
  og_image_url?: string | null;
  related?: BlogPostListItem[];
  admin_notes?: string | null;
};

export type BlogComment = {
  id: string;
  post_id: string;
  body: string;
  status: string;
  display_name: string;
  is_guest: boolean;
  /** Present only when the author has a public Fan Passport. */
  passport_path?: string | null;
  created_at: string;
  is_mine?: boolean;
  can_edit?: boolean;
  can_reply?: boolean;
  is_edited?: boolean;
  edited_at?: string | null;
  edited_by_moderator?: boolean;
  parent_comment_id?: string | null;
  depth?: number;
  reply_count?: number;
  is_staff_author?: boolean;
  /** Public staff badge only — "Pàdéyá" or "Moderator". */
  author_badge?: string | null;
  replies?: BlogComment[];
};

export type BlogCommentAdmin = BlogComment & {
  user_id?: string | null;
  guest_email?: string | null;
  archived_at?: string | null;
  archived_by?: string | null;
  updated_at?: string | null;
  edited_by_user_id?: string | null;
  edited_by_admin_id?: string | null;
};

export async function fetchBlogPosts(params?: {
  category?: string;
  tag?: string;
  author?: string;
  featured?: boolean;
  q?: string;
  limit?: number;
}): Promise<BlogPostListItem[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.tag) qs.set("tag", params.tag);
  if (params?.author) qs.set("author", params.author);
  if (params?.featured) qs.set("featured", "true");
  if (params?.q) qs.set("q", params.q);
  if (params?.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiRequest<BlogPostListItem[]>(`/blog/posts${q ? `?${q}` : ""}`, {
    auth: false,
  });
}

export async function fetchBlogPost(slug: string): Promise<BlogPost> {
  return apiRequest<BlogPost>(`/blog/posts/${encodeURIComponent(slug)}`, {
    auth: false,
  });
}

export async function fetchBlogCategories(): Promise<BlogCategory[]> {
  return apiRequest<BlogCategory[]>("/blog/categories", { auth: false });
}

export async function fetchBlogTags(): Promise<BlogTag[]> {
  return apiRequest<BlogTag[]>("/blog/tags", { auth: false });
}

export async function fetchBlogAuthors(): Promise<BlogAuthor[]> {
  return apiRequest<BlogAuthor[]>("/blog/authors", { auth: false });
}

export async function fetchBlogAuthor(slug: string): Promise<BlogAuthor> {
  return apiRequest<BlogAuthor>(`/blog/authors/${encodeURIComponent(slug)}`, {
    auth: false,
  });
}

export async function fetchBlogCategory(slug: string): Promise<BlogCategory> {
  return apiRequest<BlogCategory>(
    `/blog/categories/${encodeURIComponent(slug)}`,
    { auth: false },
  );
}

export async function fetchBlogTag(slug: string): Promise<BlogTag> {
  return apiRequest<BlogTag>(`/blog/tags/${encodeURIComponent(slug)}`, {
    auth: false,
  });
}

export async function fetchBlogComments(slug: string): Promise<BlogComment[]> {
  return apiRequest<BlogComment[]>(
    `/blog/posts/${encodeURIComponent(slug)}/comments`,
    // Attach token when present so is_mine can resolve for the viewer
  );
}

export async function createBlogComment(
  slug: string,
  body: {
    body: string;
    guest_name?: string;
    website?: string;
  },
): Promise<BlogComment> {
  return apiRequest<BlogComment>(
    `/blog/posts/${encodeURIComponent(slug)}/comments`,
    {
      method: "POST",
      body,
    },
  );
}

export async function withdrawBlogComment(commentId: string): Promise<void> {
  await apiRequest<void>(`/blog/comments/${commentId}`, { method: "DELETE" });
}

export async function updateBlogComment(
  commentId: string,
  body: { body: string; edit_reason?: string },
): Promise<BlogComment> {
  return apiRequest<BlogComment>(`/blog/comments/${commentId}`, {
    method: "PATCH",
    body,
  });
}

export async function replyToBlogComment(
  commentId: string,
  body: {
    body: string;
    guest_name?: string;
    website?: string;
  },
): Promise<BlogComment> {
  return apiRequest<BlogComment>(`/blog/comments/${commentId}/reply`, {
    method: "POST",
    body,
  });
}

export async function fetchAdminBlogComments(params?: {
  post_id?: string;
  status?: string;
  limit?: number;
}): Promise<BlogCommentAdmin[]> {
  const qs = new URLSearchParams();
  if (params?.post_id) qs.set("post_id", params.post_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiRequest<BlogCommentAdmin[]>(
    `/admin/blog/comments${q ? `?${q}` : ""}`,
  );
}

export async function fetchAdminBlogPosts(includeArchived = false) {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<BlogPost[]>(`/admin/blog/posts${q}`);
}

export async function fetchAdminBlogPost(id: string) {
  return apiRequest<BlogPost>(`/admin/blog/posts/${id}`);
}

export async function createAdminBlogPost(body: Record<string, unknown>) {
  return apiRequest<BlogPost>("/admin/blog/posts", {
    method: "POST",
    body,
  });
}

export async function updateAdminBlogPost(
  id: string,
  body: Record<string, unknown>,
) {
  return apiRequest<BlogPost>(`/admin/blog/posts/${id}`, {
    method: "PATCH",
    body,
  });
}

async function revalidatePublicBlog(): Promise<void> {
  try {
    await fetch("/api/revalidate/blog", { method: "POST" });
  } catch {
    /* public pages refresh on next ISR window */
  }
}

export async function publishAdminBlogPost(id: string) {
  const post = await apiRequest<BlogPost>(`/admin/blog/posts/${id}/publish`, {
    method: "POST",
  });
  await revalidatePublicBlog();
  return post;
}

export async function unpublishAdminBlogPost(id: string) {
  const post = await apiRequest<BlogPost>(
    `/admin/blog/posts/${id}/unpublish`,
    { method: "POST" },
  );
  await revalidatePublicBlog();
  return post;
}

export async function deleteAdminBlogPost(id: string) {
  await apiRequest<void>(`/admin/blog/posts/${id}`, { method: "DELETE" });
  await revalidatePublicBlog();
}

export async function checkBlogSlug(slug: string, excludeId?: string) {
  const qs = new URLSearchParams({ slug });
  if (excludeId) qs.set("exclude_id", excludeId);
  return apiRequest<{ slug: string; available: boolean }>(
    `/admin/blog/slug-check?${qs}`,
  );
}

export async function fetchAdminBlogCategories() {
  return apiRequest<BlogCategory[]>("/admin/blog/categories");
}

export async function createAdminBlogCategory(body: {
  name: string;
  slug?: string;
  description?: string;
}) {
  return apiRequest<BlogCategory>("/admin/blog/categories", {
    method: "POST",
    body,
  });
}

export async function fetchAdminBlogTags() {
  return apiRequest<BlogTag[]>("/admin/blog/tags");
}

export async function createAdminBlogTag(body: { name: string; slug?: string }) {
  return apiRequest<BlogTag>("/admin/blog/tags", {
    method: "POST",
    body,
  });
}

export async function fetchAdminBlogAuthors() {
  return apiRequest<BlogAuthor[]>("/admin/blog/authors");
}

export async function seedAdminBlog() {
  const result = await apiRequest<Record<string, unknown>>("/admin/blog/seed", {
    method: "POST",
  });
  await revalidatePublicBlog();
  return result;
}

/** Server-side fetch for RSC / sitemap (no auth cookie). */
function apiRoot(): string {
  const base = getApiBaseUrl();
  const prefix = getApiPrefix();
  // Server must hit the backend directly (empty base = browser same-origin only).
  const origin = base || "http://127.0.0.1:8000";
  return `${origin}${prefix}`;
}

const BLOG_FETCH = { next: { revalidate: 300, tags: ["blog"] as string[] } };

export async function fetchBlogPostsServer(params?: {
  category?: string;
  tag?: string;
  author?: string;
  limit?: number;
}): Promise<BlogPostListItem[]> {
  try {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.tag) qs.set("tag", params.tag);
    if (params?.author) qs.set("author", params.author);
    qs.set("limit", String(params?.limit ?? 50));
    const res = await fetch(`${apiRoot()}/blog/posts?${qs}`, BLOG_FETCH);
    if (!res.ok) return [];
    return (await res.json()) as BlogPostListItem[];
  } catch {
    return [];
  }
}

export const fetchBlogPostServer = cache(async (
  slug: string,
): Promise<BlogPost | null> => {
  try {
    const res = await fetch(
      `${apiRoot()}/blog/posts/${encodeURIComponent(slug)}`,
      BLOG_FETCH,
    );
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return (await res.json()) as BlogPost;
  } catch {
    return null;
  }
});

export async function fetchBlogCategoriesServer(): Promise<BlogCategory[]> {
  try {
    const res = await fetch(`${apiRoot()}/blog/categories`, BLOG_FETCH);
    if (!res.ok) return [];
    return (await res.json()) as BlogCategory[];
  } catch {
    return [];
  }
}

export async function fetchBlogTagsServer(): Promise<BlogTag[]> {
  try {
    const res = await fetch(`${apiRoot()}/blog/tags`, BLOG_FETCH);
    if (!res.ok) return [];
    return (await res.json()) as BlogTag[];
  } catch {
    return [];
  }
}

export async function fetchBlogAuthorsServer(): Promise<BlogAuthor[]> {
  try {
    const res = await fetch(`${apiRoot()}/blog/authors`, BLOG_FETCH);
    if (!res.ok) return [];
    return (await res.json()) as BlogAuthor[];
  } catch {
    return [];
  }
}

export async function fetchBlogTaxonomyServer(
  kind: "categories" | "tags" | "authors",
  slug: string,
): Promise<BlogCategory | BlogTag | BlogAuthor | null> {
  try {
    const res = await fetch(
      `${apiRoot()}/blog/${kind}/${encodeURIComponent(slug)}`,
      BLOG_FETCH,
    );
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return (await res.json()) as BlogCategory | BlogTag | BlogAuthor;
  } catch {
    return null;
  }
}
