/** Blog document API — structured content, templates, reusable sections. */

import { apiRequest } from "@/lib/api";
import type {
  BlogContentDocument,
  HeroSettings,
  LayoutTemplate,
  ReusableSection,
} from "@/lib/blog-document";
import type { BlogPost } from "@/lib/blog-api";

export type DocumentResponse = {
  content_document: BlogContentDocument;
  content_document_version: number;
  content_version: number;
  editor_mode: string | null;
  hero_settings: HeroSettings | null;
  has_legacy_body_only: boolean;
};

export async function fetchBlogDocument(postId: string): Promise<DocumentResponse> {
  return apiRequest<DocumentResponse>(`/admin/blog/posts/${postId}/document`);
}

export async function patchBlogDocument(
  postId: string,
  payload: {
    content_document: BlogContentDocument;
    hero_settings?: HeroSettings | null;
    editor_mode?: string | null;
    expected_content_version: number;
  },
): Promise<BlogPost> {
  return apiRequest<BlogPost>(`/admin/blog/posts/${postId}/document`, {
    method: "PATCH",
    body: payload,
  });
}

export async function validateBlogDocument(
  postId: string,
  content_document: BlogContentDocument,
) {
  return apiRequest<{ valid: boolean; document?: BlogContentDocument; errors?: string[] }>(
    `/admin/blog/posts/${postId}/document/validate`,
    { method: "POST", body: { content_document } },
  );
}

export async function convertBlogDocument(postId: string) {
  return apiRequest<{
    content_document: BlogContentDocument;
    warning?: string | null;
    revision_id?: string;
  }>(`/admin/blog/posts/${postId}/document/convert`, { method: "POST" });
}

export async function fetchLayoutTemplates(): Promise<LayoutTemplate[]> {
  return apiRequest<LayoutTemplate[]>("/admin/blog/layout-templates");
}

export async function fetchReusableSections(): Promise<ReusableSection[]> {
  return apiRequest<ReusableSection[]>("/admin/blog/reusable-sections");
}

export async function createReusableSection(payload: {
  name: string;
  slug?: string;
  description?: string;
  section: Record<string, unknown>;
}) {
  return apiRequest<ReusableSection>("/admin/blog/reusable-sections", {
    method: "POST",
    body: payload,
  });
}
