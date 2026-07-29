/** Pure utility functions for the blog workspace UI. */

export type WorkspaceTab = "plan" | "write" | "design" | "seo" | "review" | "publish";

const VALID_TABS: WorkspaceTab[] = ["plan", "write", "design", "seo", "review", "publish"];

export function validateTab(raw: string | null | undefined): WorkspaceTab {
  if (raw && (VALID_TABS as string[]).includes(raw)) {
    return raw as WorkspaceTab;
  }
  return "write";
}

export type AutosaveStatus = "idle" | "saving" | "saved" | "failed" | "conflict";

export function autosaveStatusText(status: AutosaveStatus): string {
  switch (status) {
    case "saving":
      return "Saving…";
    case "saved":
      return "Saved";
    case "failed":
      return "Save failed";
    case "conflict":
      return "Conflict";
    default:
      return "";
  }
}

export type ChecklistPost = {
  title?: string;
  slug?: string;
  seoTitle?: string;
  seoDescription?: string;
  focusKeyword?: string;
};

export type ChecklistDocument = {
  blocks?: Array<{ type?: string; props?: Record<string, unknown> }>;
};

export type ChecklistItem = {
  id: string;
  label: string;
  ok: boolean;
  fixTab?: WorkspaceTab;
};

export function computeChecklist(
  post: ChecklistPost,
  doc: ChecklistDocument,
): ChecklistItem[] {
  const blocks = doc.blocks ?? [];
  const hasH2 = blocks.some((b) => b.type === "heading" && b.props?.level === 2);
  const imagesMissingAlt = blocks.filter(
    (b) => b.type === "image" && !b.props?.alt,
  ).length;

  return [
    { id: "title", label: "Title provided", ok: Boolean(post.title?.trim()), fixTab: "write" },
    { id: "h2", label: "Article has H2 headings", ok: hasH2, fixTab: "write" },
    { id: "image_alt", label: "No images missing alt text", ok: imagesMissingAlt === 0, fixTab: "design" },
    { id: "meta_title", label: "Meta title set", ok: Boolean(post.seoTitle?.trim()), fixTab: "seo" },
    { id: "meta_desc", label: "Meta description set", ok: Boolean(post.seoDescription?.trim()) && (post.seoDescription?.length ?? 0) >= 50, fixTab: "seo" },
    { id: "slug", label: "Slug set", ok: Boolean(post.slug?.trim()), fixTab: "seo" },
    { id: "keyword_title", label: "Focus keyword in title", ok: Boolean(post.focusKeyword?.trim() && post.title?.toLowerCase().includes(post.focusKeyword.toLowerCase())), fixTab: "seo" },
  ];
}

export function seoTitleScore(title: string): { ok: boolean; message: string } {
  const len = title.length;
  if (len === 0) return { ok: false, message: "No title" };
  if (len < 50) return { ok: false, message: `Too short (${len}/50–60)` };
  if (len > 60) return { ok: false, message: `Too long (${len}/50–60)` };
  return { ok: true, message: `Good length (${len})` };
}

export function seoDescriptionScore(desc: string): { ok: boolean; message: string } {
  const len = desc.length;
  if (len === 0) return { ok: false, message: "No description" };
  if (len < 120) return { ok: false, message: `Too short (${len}/120–160)` };
  if (len > 160) return { ok: false, message: `Too long (${len}/120–160)` };
  return { ok: true, message: `Good length (${len})` };
}
