/** Blog API types + client helpers. */

import { cache } from "react";

import { apiRequest } from "@/lib/api";
import { API_TIMEOUT_MS } from "@/lib/api-timeouts";
import { fetchPublicJson } from "@/lib/cache/public-api";

export type BlogCategory = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
  archived_at?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  usage_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type BlogTag = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
  archived_at?: string | null;
  usage_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type BlogPostType = {
  id: string;
  key: string;
  name: string;
  slug: string;
  description?: string | null;
  sort_order?: number;
  is_system?: boolean;
  is_active?: boolean;
  archived_at?: string | null;
  usage_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type BlogMediaRole = {
  id: string;
  key: string;
  name: string;
  description?: string | null;
  sort_order?: number;
  is_system?: boolean;
  is_required?: boolean;
  storage_folder?: string;
  allowed_contexts?: string[];
  is_active?: boolean;
  archived_at?: string | null;
  usage_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
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
  post_type?: BlogPostType | null;
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
  og_title?: string | null;
  social_share_text?: string | null;
  focus_keyword?: string | null;
  secondary_keywords?: string[] | null;
  related?: BlogPostListItem[];
  admin_notes?: string | null;
  content_version?: number;
  content_document?: Record<string, unknown> | null;
  content_document_version?: number;
  editor_mode?: string | null;
  hero_settings?: Record<string, unknown> | null;
  studio_brief?: Record<string, unknown> | null;
  studio_outline?: Record<string, unknown> | null;
  faqs?: Array<{ id: string; question: string; answer: string }> | null;
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
    timeout: "mutation",
  });
}

export async function updateAdminBlogPost(
  id: string,
  body: Record<string, unknown>,
) {
  return apiRequest<BlogPost>(`/admin/blog/posts/${id}`, {
    method: "PATCH",
    body,
    timeout: "mutation",
  });
}

async function revalidatePublicBlog(): Promise<void> {
  // Fire-and-forget with a short timeout so mutations never hang on ISR bust.
  void fetch("/api/revalidate/blog", {
    method: "POST",
    signal: AbortSignal.timeout(2_500),
  }).catch(() => {
    /* public pages refresh on next ISR window */
  });
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

export async function fetchAdminBlogCategories(opts?: {
  includeArchived?: boolean;
  activeOnly?: boolean;
}) {
  const qs = new URLSearchParams();
  if (opts?.includeArchived) qs.set("include_archived", "true");
  if (opts?.activeOnly) qs.set("active_only", "true");
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<BlogCategory[]>(`/admin/blog/categories${suffix}`);
}

export async function createAdminBlogCategory(body: {
  name: string;
  slug?: string;
  description?: string;
  sort_order?: number;
  seo_title?: string;
  seo_description?: string;
}) {
  const row = await apiRequest<BlogCategory>("/admin/blog/categories", {
    method: "POST",
    body,
  });
  await revalidatePublicBlog();
  return row;
}

export async function updateAdminBlogCategory(
  id: string,
  body: {
    name?: string;
    slug?: string;
    description?: string | null;
    sort_order?: number;
    seo_title?: string | null;
    seo_description?: string | null;
    confirm_slug_change?: boolean;
  },
) {
  const row = await apiRequest<BlogCategory>(`/admin/blog/categories/${id}`, {
    method: "PATCH",
    body,
  });
  await revalidatePublicBlog();
  return row;
}

export async function archiveAdminBlogCategory(id: string) {
  const row = await apiRequest<BlogCategory>(`/admin/blog/categories/${id}/archive`, {
    method: "POST",
  });
  await revalidatePublicBlog();
  return row;
}

export async function restoreAdminBlogCategory(id: string) {
  const row = await apiRequest<BlogCategory>(`/admin/blog/categories/${id}/restore`, {
    method: "POST",
  });
  await revalidatePublicBlog();
  return row;
}

export async function reorderAdminBlogCategories(orderedIds: string[]) {
  const rows = await apiRequest<BlogCategory[]>("/admin/blog/categories/reorder", {
    method: "POST",
    body: { ordered_ids: orderedIds },
  });
  await revalidatePublicBlog();
  return rows;
}

export async function fetchAdminBlogTags(opts?: {
  includeArchived?: boolean;
  activeOnly?: boolean;
}) {
  const qs = new URLSearchParams();
  if (opts?.includeArchived) qs.set("include_archived", "true");
  if (opts?.activeOnly) qs.set("active_only", "true");
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<BlogTag[]>(`/admin/blog/tags${suffix}`);
}

export async function createAdminBlogTag(body: {
  name: string;
  slug?: string;
  description?: string;
  sort_order?: number;
}) {
  const row = await apiRequest<BlogTag>("/admin/blog/tags", {
    method: "POST",
    body,
  });
  await revalidatePublicBlog();
  return row;
}

export async function updateAdminBlogTag(
  id: string,
  body: {
    name?: string;
    slug?: string;
    description?: string | null;
    sort_order?: number;
    confirm_slug_change?: boolean;
  },
) {
  const row = await apiRequest<BlogTag>(`/admin/blog/tags/${id}`, {
    method: "PATCH",
    body,
  });
  await revalidatePublicBlog();
  return row;
}

export async function archiveAdminBlogTag(id: string) {
  const row = await apiRequest<BlogTag>(`/admin/blog/tags/${id}/archive`, {
    method: "POST",
  });
  await revalidatePublicBlog();
  return row;
}

export async function restoreAdminBlogTag(id: string) {
  const row = await apiRequest<BlogTag>(`/admin/blog/tags/${id}/restore`, {
    method: "POST",
  });
  await revalidatePublicBlog();
  return row;
}

export async function reorderAdminBlogTags(orderedIds: string[]) {
  const rows = await apiRequest<BlogTag[]>("/admin/blog/tags/reorder", {
    method: "POST",
    body: { ordered_ids: orderedIds },
  });
  await revalidatePublicBlog();
  return rows;
}

export async function fetchAdminBlogPostTypes(opts?: {
  includeArchived?: boolean;
  activeOnly?: boolean;
}) {
  const qs = new URLSearchParams();
  if (opts?.includeArchived) qs.set("include_archived", "true");
  if (opts?.activeOnly) qs.set("active_only", "true");
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<BlogPostType[]>(`/admin/blog/post-types${suffix}`);
}

export async function createAdminBlogPostType(body: {
  name: string;
  key?: string;
  slug?: string;
  description?: string;
  sort_order?: number;
}) {
  const row = await apiRequest<BlogPostType>("/admin/blog/post-types", {
    method: "POST",
    body,
  });
  await revalidatePublicBlog();
  return row;
}

export async function updateAdminBlogPostType(
  id: string,
  body: {
    name?: string;
    slug?: string;
    description?: string | null;
    sort_order?: number;
  },
) {
  const row = await apiRequest<BlogPostType>(`/admin/blog/post-types/${id}`, {
    method: "PATCH",
    body,
  });
  await revalidatePublicBlog();
  return row;
}

export async function archiveAdminBlogPostType(id: string) {
  const row = await apiRequest<BlogPostType>(`/admin/blog/post-types/${id}/archive`, {
    method: "POST",
  });
  await revalidatePublicBlog();
  return row;
}

export async function restoreAdminBlogPostType(id: string) {
  const row = await apiRequest<BlogPostType>(`/admin/blog/post-types/${id}/restore`, {
    method: "POST",
  });
  await revalidatePublicBlog();
  return row;
}

export async function reorderAdminBlogPostTypes(orderedIds: string[]) {
  const rows = await apiRequest<BlogPostType[]>("/admin/blog/post-types/reorder", {
    method: "POST",
    body: { ordered_ids: orderedIds },
  });
  await revalidatePublicBlog();
  return rows;
}

export async function fetchAdminBlogMediaRoles(opts?: {
  includeArchived?: boolean;
  activeOnly?: boolean;
}) {
  const qs = new URLSearchParams();
  if (opts?.includeArchived) qs.set("include_archived", "true");
  if (opts?.activeOnly) qs.set("active_only", "true");
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<BlogMediaRole[]>(`/admin/blog/media-roles${suffix}`);
}

export async function createAdminBlogMediaRole(body: {
  name: string;
  key: string;
  description?: string;
  sort_order?: number;
  storage_folder?: string;
  allowed_contexts?: string[];
}) {
  return apiRequest<BlogMediaRole>("/admin/blog/media-roles", {
    method: "POST",
    body,
  });
}

export async function updateAdminBlogMediaRole(
  id: string,
  body: {
    name?: string;
    description?: string | null;
    sort_order?: number;
    allowed_contexts?: string[];
  },
) {
  return apiRequest<BlogMediaRole>(`/admin/blog/media-roles/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function archiveAdminBlogMediaRole(id: string) {
  return apiRequest<BlogMediaRole>(`/admin/blog/media-roles/${id}/archive`, {
    method: "POST",
  });
}

export async function restoreAdminBlogMediaRole(id: string) {
  return apiRequest<BlogMediaRole>(`/admin/blog/media-roles/${id}/restore`, {
    method: "POST",
  });
}

export async function reorderAdminBlogMediaRoles(orderedIds: string[]) {
  return apiRequest<BlogMediaRole[]>("/admin/blog/media-roles/reorder", {
    method: "POST",
    body: { ordered_ids: orderedIds },
  });
}

export async function uploadBlogMedia(
  file: File,
  mediaRoleKey: string = "inline",
): Promise<{ url: string; key: string; media_role_key: string }> {
  const { apiUpload } = await import("@/lib/api");
  const form = new FormData();
  form.append("file", file);
  form.append("media_role_key", mediaRoleKey);
  return apiUpload("/admin/blog/media/upload", form);
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
const BLOG_NEXT = { revalidate: 300, tags: ["blog"] as string[] };

export async function fetchBlogPostsServer(params?: {
  category?: string;
  tag?: string;
  author?: string;
  limit?: number;
}): Promise<BlogPostListItem[]> {
  const qs = new URLSearchParams();
  if (params?.category) qs.set("category", params.category);
  if (params?.tag) qs.set("tag", params.tag);
  if (params?.author) qs.set("author", params.author);
  qs.set("limit", String(params?.limit ?? 50));
  const rows = await fetchPublicJson<BlogPostListItem[]>(`/blog/posts?${qs}`, {
    next: BLOG_NEXT,
    timeoutMs: API_TIMEOUT_MS.public,
  });
  return rows ?? [];
}

export const fetchBlogPostServer = cache(async (
  slug: string,
): Promise<BlogPost | null> => {
  return fetchPublicJson<BlogPost>(
    `/blog/posts/${encodeURIComponent(slug)}`,
    { next: BLOG_NEXT, timeoutMs: API_TIMEOUT_MS.public },
  );
});

export async function fetchBlogCategoriesServer(): Promise<BlogCategory[]> {
  const rows = await fetchPublicJson<BlogCategory[]>("/blog/categories", {
    next: BLOG_NEXT,
    timeoutMs: API_TIMEOUT_MS.public,
  });
  return rows ?? [];
}

export async function fetchBlogTagsServer(): Promise<BlogTag[]> {
  const rows = await fetchPublicJson<BlogTag[]>("/blog/tags", {
    next: BLOG_NEXT,
    timeoutMs: API_TIMEOUT_MS.public,
  });
  return rows ?? [];
}

export async function fetchBlogAuthorsServer(): Promise<BlogAuthor[]> {
  const rows = await fetchPublicJson<BlogAuthor[]>("/blog/authors", {
    next: BLOG_NEXT,
    timeoutMs: API_TIMEOUT_MS.public,
  });
  return rows ?? [];
}

export async function fetchBlogTaxonomyServer(
  kind: "categories" | "tags" | "authors",
  slug: string,
): Promise<BlogCategory | BlogTag | BlogAuthor | null> {
  return fetchPublicJson<BlogCategory | BlogTag | BlogAuthor>(
    `/blog/${kind}/${encodeURIComponent(slug)}`,
    { next: BLOG_NEXT, timeoutMs: API_TIMEOUT_MS.public },
  );
}
