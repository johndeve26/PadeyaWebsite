/** Blog AI Studio API client — admin studio endpoints. */

import { apiRequest } from "@/lib/api";
import type { BlogPost } from "@/lib/blog-api";

import type {
  BlogContentBrief,
  BlogFactClaim,
  BlogFaqItem,
  BlogImagePrompt,
  BlogInternalLinkSuggestion,
  BlogOutline,
  BlogOutlineSection,
  BlogQualityReview,
  BlogRevisionPublic,
  BlogSeoBrief,
  BlogSeoScore,
  BlogSimilarityReview,
  BlogTitleSuggestion,
  FullDraftProgressResponse,
  RewriteAction,
  StudioAutosaveRequest,
  StudioAutosaveResponse,
} from "@/components/blog/studio/types";

type StudioBase = {
  brief?: BlogContentBrief | null;
  outline?: BlogOutline | null;
  blog_post_id?: string | null;
  client_request_id?: string;
  title?: string;
  excerpt?: string;
  body?: string;
  slug?: string;
  focus_keyword?: string;
  secondary_keywords?: string[];
  locked_section_ids?: string[];
};

function postAi<T>(path: string, body: Record<string, unknown>) {
  return apiRequest<T>(`/admin/blog/ai/${path}`, {
    method: "POST",
    body,
    timeout: "long",
  });
}

export async function studioGenerateSeoBrief(payload: StudioBase) {
  return postAi<BlogSeoBrief>("seo-brief", payload as Record<string, unknown>);
}

export async function studioGenerateTitles(payload: StudioBase) {
  return postAi<{ titles?: BlogTitleSuggestion[]; options?: BlogTitleSuggestion[] } | BlogTitleSuggestion[]>(
    "titles",
    payload as Record<string, unknown>,
  );
}

export function normalizeTitleSuggestions(
  res:
    | { titles?: BlogTitleSuggestion[]; options?: BlogTitleSuggestion[] }
    | BlogTitleSuggestion[],
): BlogTitleSuggestion[] {
  if (Array.isArray(res)) return res;
  return res.titles || res.options || [];
}

export async function studioGenerateOutline(payload: StudioBase) {
  return postAi<BlogOutline>("outline", payload as Record<string, unknown>);
}

export async function studioRegenerateOutlineSection(
  payload: StudioBase & {
    section_id: string;
    section?: BlogOutlineSection;
  },
) {
  return postAi<BlogOutlineSection | BlogOutline>(
    "outline/section",
    payload as Record<string, unknown>,
  );
}

export async function studioGenerateSection(
  payload: StudioBase & {
    section_id: string;
    section?: BlogOutlineSection;
  },
) {
  return postAi<{
    section?: { id?: string; heading?: string; body?: string; markdown?: string };
    body?: string;
    markdown?: string;
  }>("section", payload as Record<string, unknown>);
}

export async function studioGenerateFullDraft(payload: StudioBase) {
  return postAi<FullDraftProgressResponse>(
    "full-draft",
    payload as Record<string, unknown>,
  );
}

export async function studioRewriteSelection(
  payload: StudioBase & {
    selection: string;
    action: RewriteAction | string;
    tone?: string;
  },
) {
  return postAi<{
    rewritten?: string;
    suggestion?: string;
    text?: string;
  }>("rewrite", payload as Record<string, unknown>);
}

export async function studioReviewArticle(payload: StudioBase) {
  return postAi<BlogQualityReview>("review", payload as Record<string, unknown>);
}

export async function studioSimilarityReview(payload: StudioBase) {
  return postAi<BlogSimilarityReview>(
    "similarity",
    payload as Record<string, unknown>,
  );
}

export async function studioGenerateFaqs(payload: StudioBase) {
  return postAi<{ faqs?: BlogFaqItem[] } | BlogFaqItem[]>(
    "faqs",
    payload as Record<string, unknown>,
  );
}

export function normalizeFaqs(
  res: { faqs?: BlogFaqItem[] } | BlogFaqItem[],
): BlogFaqItem[] {
  if (Array.isArray(res)) return res;
  return res.faqs || [];
}

export async function studioGenerateImagePrompt(payload: StudioBase) {
  return postAi<BlogImagePrompt>(
    "image-prompt",
    payload as Record<string, unknown>,
  );
}

export async function studioSuggestInternalLinks(payload: StudioBase) {
  return postAi<
    { suggestions?: BlogInternalLinkSuggestion[] } | BlogInternalLinkSuggestion[]
  >("internal-links", payload as Record<string, unknown>);
}

export function normalizeInternalLinks(
  res:
    | { suggestions?: BlogInternalLinkSuggestion[] }
    | BlogInternalLinkSuggestion[],
): BlogInternalLinkSuggestion[] {
  if (Array.isArray(res)) return res;
  return res.suggestions || [];
}

export async function studioFactReview(payload: StudioBase) {
  return postAi<{ claims?: BlogFactClaim[] } | BlogFactClaim[]>(
    "fact-review",
    payload as Record<string, unknown>,
  );
}

export function normalizeFactClaims(
  res: { claims?: BlogFactClaim[] } | BlogFactClaim[],
): BlogFactClaim[] {
  if (Array.isArray(res)) return res;
  return res.claims || [];
}

export async function studioSeoScore(payload: StudioBase & {
  cover_url?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  image_alt?: string | null;
}) {
  return postAi<BlogSeoScore>("seo-score", payload as Record<string, unknown>);
}

export async function studioAutosave(
  postId: string,
  body: StudioAutosaveRequest,
) {
  return apiRequest<StudioAutosaveResponse>(
    `/admin/blog/posts/${postId}/autosave`,
    { method: "POST", body },
  );
}

export async function studioListRevisions(postId: string) {
  return apiRequest<BlogRevisionPublic[]>(
    `/admin/blog/posts/${postId}/revisions`,
  );
}

export async function studioGetRevision(postId: string, revisionId: string) {
  return apiRequest<BlogRevisionPublic>(
    `/admin/blog/posts/${postId}/revisions/${revisionId}`,
  );
}

export async function studioRestoreRevision(
  postId: string,
  revisionId: string,
) {
  return apiRequest<BlogPost>(
    `/admin/blog/posts/${postId}/revisions/${revisionId}/restore`,
    { method: "POST" },
  );
}

export async function studioCheckpointRevision(
  postId: string,
  body?: { summary?: string },
) {
  return apiRequest<BlogRevisionPublic>(
    `/admin/blog/posts/${postId}/revisions/checkpoint`,
    { method: "POST", body: body || {} },
  );
}

export async function studioPreviewPost(postId: string) {
  return apiRequest<BlogPost>(`/admin/blog/preview/${postId}`);
}
