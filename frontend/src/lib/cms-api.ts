import { apiRequest } from "@/lib/api";
import type {
  CmsBanner,
  CmsBlogPost,
  CmsBrowseTile,
  CmsFaq,
} from "@/lib/types/lifecycle";

export async function fetchAdminBlogPosts(
  includeArchived = false,
): Promise<CmsBlogPost[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<CmsBlogPost[]>(`/cms/admin/blog${q}`);
}

export async function createBlogPost(body: {
  title: string;
  slug?: string;
  excerpt?: string;
  body: string;
  cover_url?: string;
}): Promise<CmsBlogPost> {
  return apiRequest<CmsBlogPost>("/cms/admin/blog", { method: "POST", body });
}

export async function updateBlogPost(
  id: string,
  body: Partial<{
    title: string;
    slug: string;
    excerpt: string;
    body: string;
    cover_url: string;
  }>,
): Promise<CmsBlogPost> {
  return apiRequest<CmsBlogPost>(`/cms/admin/blog/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function publishBlogPost(id: string): Promise<CmsBlogPost> {
  return apiRequest<CmsBlogPost>(`/cms/admin/blog/${id}/publish`, {
    method: "POST",
  });
}

export async function archiveBlogPost(id: string): Promise<CmsBlogPost> {
  return apiRequest<CmsBlogPost>(`/cms/admin/blog/${id}/archive`, {
    method: "POST",
  });
}

export async function restoreBlogPost(id: string): Promise<CmsBlogPost> {
  return apiRequest<CmsBlogPost>(`/cms/admin/blog/${id}/restore`, {
    method: "POST",
  });
}

export async function fetchAdminFaqs(includeArchived = false): Promise<CmsFaq[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<CmsFaq[]>(`/cms/admin/faqs${q}`);
}

export async function createFaq(body: {
  question: string;
  answer: string;
  category?: string;
  sort_order?: number;
}): Promise<CmsFaq> {
  return apiRequest<CmsFaq>("/cms/admin/faqs", { method: "POST", body });
}

export async function updateFaq(
  id: string,
  body: Partial<{
    question: string;
    answer: string;
    category: string;
    sort_order: number;
  }>,
): Promise<CmsFaq> {
  return apiRequest<CmsFaq>(`/cms/admin/faqs/${id}`, { method: "PATCH", body });
}

export async function publishFaq(id: string): Promise<CmsFaq> {
  return apiRequest<CmsFaq>(`/cms/admin/faqs/${id}/publish`, { method: "POST" });
}

export async function archiveFaq(id: string): Promise<CmsFaq> {
  return apiRequest<CmsFaq>(`/cms/admin/faqs/${id}/archive`, { method: "POST" });
}

export async function restoreFaq(id: string): Promise<CmsFaq> {
  return apiRequest<CmsFaq>(`/cms/admin/faqs/${id}/restore`, { method: "POST" });
}

export async function fetchAdminBanners(
  includeArchived = false,
): Promise<CmsBanner[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<CmsBanner[]>(`/cms/admin/banners${q}`);
}

export async function createBanner(body: {
  title: string;
  subtitle?: string;
  image_url: string;
  cta_label?: string;
  cta_href?: string;
  sort_order?: number;
}): Promise<CmsBanner> {
  return apiRequest<CmsBanner>("/cms/admin/banners", { method: "POST", body });
}

export async function updateBanner(
  id: string,
  body: Partial<{
    title: string;
    subtitle: string;
    image_url: string;
    cta_label: string;
    cta_href: string;
    sort_order: number;
  }>,
): Promise<CmsBanner> {
  return apiRequest<CmsBanner>(`/cms/admin/banners/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function publishBanner(id: string): Promise<CmsBanner> {
  return apiRequest<CmsBanner>(`/cms/admin/banners/${id}/publish`, {
    method: "POST",
  });
}

export async function archiveBanner(id: string): Promise<CmsBanner> {
  return apiRequest<CmsBanner>(`/cms/admin/banners/${id}/archive`, {
    method: "POST",
  });
}

export async function restoreBanner(id: string): Promise<CmsBanner> {
  return apiRequest<CmsBanner>(`/cms/admin/banners/${id}/restore`, {
    method: "POST",
  });
}

export async function fetchPublicBrowseTiles(): Promise<CmsBrowseTile[]> {
  return apiRequest<CmsBrowseTile[]>("/cms/browse-tiles");
}

export async function fetchAdminBrowseTiles(
  includeArchived = false,
): Promise<CmsBrowseTile[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<CmsBrowseTile[]>(`/cms/admin/browse-tiles${q}`);
}

export async function createBrowseTile(body: {
  rail: string;
  label: string;
  hint?: string;
  href: string;
  image_url: string;
  sort_order?: number;
}): Promise<CmsBrowseTile> {
  return apiRequest<CmsBrowseTile>("/cms/admin/browse-tiles", {
    method: "POST",
    body,
  });
}

export async function updateBrowseTile(
  id: string,
  body: Partial<{
    rail: string;
    label: string;
    hint: string;
    href: string;
    image_url: string;
    sort_order: number;
  }>,
): Promise<CmsBrowseTile> {
  return apiRequest<CmsBrowseTile>(`/cms/admin/browse-tiles/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function publishBrowseTile(id: string): Promise<CmsBrowseTile> {
  return apiRequest<CmsBrowseTile>(`/cms/admin/browse-tiles/${id}/publish`, {
    method: "POST",
  });
}

export async function archiveBrowseTile(id: string): Promise<CmsBrowseTile> {
  return apiRequest<CmsBrowseTile>(`/cms/admin/browse-tiles/${id}/archive`, {
    method: "POST",
  });
}

export async function restoreBrowseTile(id: string): Promise<CmsBrowseTile> {
  return apiRequest<CmsBrowseTile>(`/cms/admin/browse-tiles/${id}/restore`, {
    method: "POST",
  });
}

export async function seedDefaultBrowseTiles(): Promise<{
  created: number;
  status: string;
}> {
  return apiRequest<{ created: number; status: string }>(
    "/cms/admin/browse-tiles/seed-defaults",
    { method: "POST" },
  );
}
