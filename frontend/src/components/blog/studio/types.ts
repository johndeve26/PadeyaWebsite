/** Blog AI Studio types — mirrors backend studio schemas (flexible/optional). */

export const BLOG_CONTENT_TYPES = [
  "How-to guide",
  "Event planning guide",
  "Industry insight",
  "Venue guide",
  "Host resource",
  "Attendee guide",
  "Product update",
  "Case study",
  "List article",
  "News analysis",
  "Editorial",
] as const;

export const BLOG_SEARCH_INTENTS = [
  "Informational",
  "Commercial",
  "Navigational",
  "Transactional",
] as const;

export const BLOG_TONES = [
  "Professional",
  "Friendly",
  "Educational",
  "Editorial",
  "Conversational",
  "Premium",
  "Energetic",
] as const;

export const BLOG_WORKFLOW_STEPS = [
  { id: "brief", label: "Brief", description: "Topic, audience, and goals" },
  { id: "seo_brief", label: "SEO brief", description: "Keywords and angle" },
  { id: "titles", label: "Titles", description: "Pick or rewrite a title" },
  { id: "outline", label: "Outline", description: "Structure and approve" },
  { id: "draft", label: "Draft", description: "Write section by section" },
  { id: "review", label: "Review", description: "Quality, facts, links" },
  { id: "publish", label: "Publish", description: "Confirm and go live" },
] as const;

export type BlogWorkflowStepId = (typeof BLOG_WORKFLOW_STEPS)[number]["id"];

export type BlogContentBrief = {
  topic?: string;
  primary_keyword?: string;
  secondary_keywords?: string[];
  target_audience?: string;
  search_intent?: string;
  article_objective?: string;
  content_type?: string;
  tone?: string;
  custom_tone?: string;
  desired_length?: string;
  location_focus?: string;
  event_category?: string;
  competitor_urls?: string[];
  talking_points?: string[];
  points_to_avoid?: string[];
  call_to_action?: string;
};

export type BlogSeoBrief = {
  title_options?: string[];
  primary_keyword?: string;
  secondary_keywords?: string[];
  search_intent?: string;
  article_angle?: string;
  audience_questions?: string[];
  recommended_headings?: string[];
  faq_questions?: string[];
  suggested_word_count?: number;
  proposed_slug?: string;
  meta_title?: string;
  meta_description?: string;
  internal_link_topics?: string[];
  content_risks?: string[];
};

export type BlogTitleSuggestion = {
  title: string;
  angle?: string;
  estimated_intent?: string;
  length?: number;
  keyword_included?: boolean;
  click_appeal?: string;
  warning?: string | null;
};

export type BlogOutlineSection = {
  id: string;
  heading: string;
  level?: 2 | 3;
  key_point?: string;
  examples?: string[];
  data_source_needs?: string[];
  locked?: boolean;
};

export type BlogOutline = {
  introduction_purpose?: string;
  sections: BlogOutlineSection[];
  conclusion_direction?: string;
  cta_placement?: string;
  faq_section?: string | null;
  approved?: boolean;
};

export type BlogGeneratedSection = {
  id: string;
  heading: string;
  body?: string;
  bullets?: string[];
  internal_link_anchor?: string | null;
  fact_markers?: string[];
  locked?: boolean;
};

export type BlogFaqItem = {
  id: string;
  question: string;
  answer: string;
};

export type SeoIndicatorStatus = "ok" | "warn" | "fail";

export type BlogSeoIndicator = {
  status: SeoIndicatorStatus;
  message?: string;
};

export type BlogSeoScore = {
  title_length?: BlogSeoIndicator;
  meta_title_length?: BlogSeoIndicator;
  description_length?: BlogSeoIndicator;
  keyword_in_title?: BlogSeoIndicator;
  keyword_in_intro?: BlogSeoIndicator;
  keyword_in_headings?: BlogSeoIndicator;
  slug_quality?: BlogSeoIndicator;
  heading_hierarchy?: BlogSeoIndicator;
  article_length?: BlogSeoIndicator;
  internal_links?: BlogSeoIndicator;
  image_alt?: BlogSeoIndicator;
  score?: number;
  summary?: string;
};

export type BlogQualityFinding = {
  category?: string;
  severity?: string;
  message?: string;
  suggestion?: string;
};

export type BlogQualityReview = {
  summary?: string;
  findings?: BlogQualityFinding[];
  suggested_changes?: string[];
  clarity?: number | BlogQualityFinding;
  repetition?: number | BlogQualityFinding;
  weak_intro?: number | BlogQualityFinding;
  unsupported_claims?: number | BlogQualityFinding;
  promotional?: number | BlogQualityFinding;
  keyword_stuffing?: number | BlogQualityFinding;
  heading_quality?: number | BlogQualityFinding;
  logical_flow?: number | BlogQualityFinding;
  missing_conclusion?: number | BlogQualityFinding;
  cta_quality?: number | BlogQualityFinding;
  reading_difficulty?: number | BlogQualityFinding;
  accessibility?: number | BlogQualityFinding;
  missing_alt?: number | BlogQualityFinding;
  broken_internal_links?: number | BlogQualityFinding;
};

export type BlogImagePrompt = {
  concept?: string;
  prompt?: string;
  aspect_ratio?: string;
  overlay_text?: string | null;
  alt_text?: string;
  caption?: string;
  focal_point?: string;
};

export type BlogInternalLinkSuggestion = {
  target_url: string;
  target_title?: string;
  suggested_anchor?: string;
  insertion_location?: string;
  relevance_reason?: string;
  dismissed?: boolean;
};

export type BlogFactClaim = {
  claim: string;
  section?: string;
  confidence?: string;
  source_required?: boolean;
  review_status?: string;
  source_urls?: string[];
};

export type BlogSimilarityReview = {
  duplicated_headings?: string[];
  repeated_paragraphs?: string[];
  similar_posts?: Array<{ title?: string; slug?: string; url?: string }>;
  cannibalization_risks?: string[];
  conflicting_slugs?: string[];
  disclaimer?: string;
};

export type BlogRevisionPublic = {
  id: string;
  post_id?: string;
  created_at?: string;
  created_by?: string | null;
  source?: string;
  action_type?: string;
  summary?: string | null;
  provider?: string | null;
  model?: string | null;
  title?: string | null;
  excerpt?: string | null;
  body?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  faqs?: BlogFaqItem[] | null;
  outline?: BlogOutline | null;
  brief?: BlogContentBrief | null;
};

export type BlogAiOperationPublic = {
  id: string;
  operation?: string;
  status?: string;
  provider?: string | null;
  model?: string | null;
  duration_ms?: number | null;
  token_usage?: number | null;
  error_category?: string | null;
  created_at?: string;
};

export type FullDraftProgressResponse = {
  status?: string;
  sections?: BlogGeneratedSection[];
  body_markdown?: string;
  failed_section_ids?: string[];
  message?: string;
};

export type StudioAutosaveRequest = {
  title?: string;
  slug?: string;
  excerpt?: string;
  body?: string;
  cover_url?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  canonical_url?: string | null;
  og_image_url?: string | null;
  og_title?: string | null;
  social_share_text?: string | null;
  focus_keyword?: string | null;
  secondary_keywords?: string[] | null;
  is_featured?: boolean;
  category_id?: string | null;
  author_id?: string | null;
  tag_ids?: string[];
  scheduled_at?: string | null;
  admin_notes?: string | null;
  studio_brief?: BlogContentBrief | null;
  studio_outline?: BlogOutline | null;
  faqs?: BlogFaqItem[] | null;
  expected_content_version?: number;
};

export type StudioAutosaveResponse = {
  id: string;
  content_version?: number;
  updated_at?: string;
  status?: string;
  [key: string]: unknown;
};

export type RewriteAction =
  | "rewrite"
  | "clarity"
  | "shorter"
  | "expand"
  | "tone"
  | "grammar"
  | "engaging"
  | "simplify"
  | "examples"
  | "transition"
  | "to_bullets"
  | "to_prose"
  | "heading"
  | "continue"
  | "summarize";

export type AiSuggestionState = {
  original: string;
  proposed: string;
  action: RewriteAction | string;
  start: number;
  end: number;
} | null;

export type GenerationStage =
  | "idle"
  | "preparing"
  | "seo_brief"
  | "titles"
  | "outline"
  | "section"
  | "draft"
  | "rewrite"
  | "faqs"
  | "review"
  | "image"
  | "links"
  | "facts"
  | "seo_score"
  | "finalizing";

export type AutosaveStatus = "idle" | "saving" | "saved" | "failed" | "conflict";

export type BlogStudioPostFields = {
  postId: string | null;
  title: string;
  slug: string;
  excerpt: string;
  body: string;
  coverUrl: string;
  seoTitle: string;
  seoDescription: string;
  canonicalUrl: string;
  ogImageUrl: string;
  ogTitle: string;
  socialShareText: string;
  focusKeyword: string;
  secondaryKeywords: string[];
  featured: boolean;
  categoryId: string;
  authorId: string;
  tagIds: string[];
  scheduledAt: string;
  adminNotes: string;
  status: string;
  contentVersion: number;
  bodyHtml?: string | null;
};

export function emptyBrief(): BlogContentBrief {
  return {
    topic: "",
    primary_keyword: "",
    secondary_keywords: [],
    target_audience: "",
    search_intent: "Informational",
    article_objective: "",
    content_type: "How-to guide",
    tone: "Professional",
    custom_tone: "",
    desired_length: "1200-1600 words",
    location_focus: "",
    event_category: "",
    competitor_urls: [],
    talking_points: [],
    points_to_avoid: [],
    call_to_action: "",
  };
}

export function emptyOutline(): BlogOutline {
  return {
    introduction_purpose: "",
    sections: [],
    conclusion_direction: "",
    cta_placement: "",
    faq_section: null,
    approved: false,
  };
}

export function newClientRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function newSectionId(): string {
  return `sec-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function newFaqId(): string {
  return `faq-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}
