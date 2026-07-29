"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type {
  AiSuggestionState,
  AutosaveStatus,
  BlogContentBrief,
  BlogFactClaim,
  BlogFaqItem,
  BlogImagePrompt,
  BlogInternalLinkSuggestion,
  BlogOutline,
  BlogQualityReview,
  BlogSeoBrief,
  BlogSeoScore,
  BlogSimilarityReview,
  BlogStudioPostFields,
  BlogTitleSuggestion,
  BlogWorkflowStepId,
  GenerationStage,
} from "./types";
import { emptyBrief, emptyOutline } from "./types";
import {
  defaultDocument,
  type BlogContentDocument,
  type EditorMode,
  type HeroSettings,
} from "@/lib/blog-document";

export type BlogStudioState = BlogStudioPostFields & {
  brief: BlogContentBrief;
  outline: BlogOutline;
  faqs: BlogFaqItem[];
  seoBrief: BlogSeoBrief | null;
  titleSuggestions: BlogTitleSuggestion[];
  seoScore: BlogSeoScore | null;
  qualityReview: BlogQualityReview | null;
  factClaims: BlogFactClaim[];
  internalLinks: BlogInternalLinkSuggestion[];
  similarity: BlogSimilarityReview | null;
  imagePrompt: BlogImagePrompt | null;
  workflowStep: BlogWorkflowStepId;
  generationStage: GenerationStage;
  generationMessage: string | null;
  generating: boolean;
  cancelGenerationRef: { current: boolean };
  suggestion: AiSuggestionState;
  autosaveStatus: AutosaveStatus;
  lastSavedAt: string | null;
  dirty: boolean;
  lockedSectionHeadings: string[];
  previewOpen: boolean;
  slugOk: boolean | null;
};

export type BlogStudioActions = {
  patch: (partial: Partial<BlogStudioState>) => void;
  setBrief: (brief: BlogContentBrief | ((b: BlogContentBrief) => BlogContentBrief)) => void;
  setOutline: (outline: BlogOutline | ((o: BlogOutline) => BlogOutline)) => void;
  setBody: (body: string | ((b: string) => string)) => void;
  setContentDocument: (
    doc: BlogContentDocument | ((d: BlogContentDocument) => BlogContentDocument),
  ) => void;
  setFaqs: (faqs: BlogFaqItem[] | ((f: BlogFaqItem[]) => BlogFaqItem[])) => void;
  markDirty: () => void;
  beginGeneration: (stage: GenerationStage, message?: string) => void;
  endGeneration: () => void;
  cancelGeneration: () => void;
  isCancelled: () => boolean;
  setSuggestion: (s: AiSuggestionState) => void;
  toggleSectionLock: (heading: string) => void;
  isSectionLocked: (heading: string) => boolean;
};

const BlogStudioContext = createContext<(BlogStudioState & BlogStudioActions) | null>(
  null,
);

const DEFAULT_BODY =
  "## Headline\n\nWrite in markdown. Use ::cta{label=\"Explore events\"; href=\"/events\"} for CTAs.\n";

export function initialStudioState(
  seed?: Partial<BlogStudioPostFields> & {
    brief?: BlogContentBrief;
    outline?: BlogOutline;
    faqs?: BlogFaqItem[];
  },
): BlogStudioState {
  return {
    postId: seed?.postId ?? null,
    title: seed?.title ?? "",
    slug: seed?.slug ?? "",
    excerpt: seed?.excerpt ?? "",
    body: seed?.body ?? DEFAULT_BODY,
    coverUrl: seed?.coverUrl ?? "",
    seoTitle: seed?.seoTitle ?? "",
    seoDescription: seed?.seoDescription ?? "",
    canonicalUrl: seed?.canonicalUrl ?? "",
    ogImageUrl: seed?.ogImageUrl ?? "",
    ogTitle: seed?.ogTitle ?? "",
    socialShareText: seed?.socialShareText ?? "",
    focusKeyword: seed?.focusKeyword ?? "",
    secondaryKeywords: seed?.secondaryKeywords ?? [],
    featured: seed?.featured ?? false,
    categoryId: seed?.categoryId ?? "",
    authorId: seed?.authorId ?? "",
    tagIds: seed?.tagIds ?? [],
    scheduledAt: seed?.scheduledAt ?? "",
    adminNotes: seed?.adminNotes ?? "",
    status: seed?.status ?? "draft",
    contentVersion: seed?.contentVersion ?? 1,
    bodyHtml: seed?.bodyHtml ?? null,
    contentDocument: seed?.contentDocument ?? defaultDocument(),
    contentMode: seed?.contentMode ?? null,
    editorMode: seed?.editorMode ?? "standard",
    heroSettings: seed?.heroSettings ?? null,
    brief: seed?.brief ?? emptyBrief(),
    outline: seed?.outline ?? emptyOutline(),
    faqs: seed?.faqs ?? [],
    seoBrief: null,
    titleSuggestions: [],
    seoScore: null,
    qualityReview: null,
    factClaims: [],
    internalLinks: [],
    similarity: null,
    imagePrompt: null,
    workflowStep: "brief",
    generationStage: "idle",
    generationMessage: null,
    generating: false,
    cancelGenerationRef: { current: false },
    suggestion: null,
    autosaveStatus: "idle",
    lastSavedAt: null,
    dirty: false,
    lockedSectionHeadings: [],
    previewOpen: false,
    slugOk: null,
  };
}

export function BlogStudioProvider({
  children,
  initial,
}: {
  children: ReactNode;
  initial?: Partial<BlogStudioPostFields> & {
    brief?: BlogContentBrief;
    outline?: BlogOutline;
    faqs?: BlogFaqItem[];
  };
}) {
  const [state, setState] = useState<BlogStudioState>(() =>
    initialStudioState(initial),
  );
  const cancelRef = useRef(false);

  const patch = useCallback((partial: Partial<BlogStudioState>) => {
    setState((prev) => ({ ...prev, ...partial }));
  }, []);

  const markDirty = useCallback(() => {
    setState((prev) => ({ ...prev, dirty: true }));
  }, []);

  const setBrief = useCallback(
    (brief: BlogContentBrief | ((b: BlogContentBrief) => BlogContentBrief)) => {
      setState((prev) => ({
        ...prev,
        dirty: true,
        brief: typeof brief === "function" ? brief(prev.brief) : brief,
      }));
    },
    [],
  );

  const setOutline = useCallback(
    (outline: BlogOutline | ((o: BlogOutline) => BlogOutline)) => {
      setState((prev) => ({
        ...prev,
        dirty: true,
        outline: typeof outline === "function" ? outline(prev.outline) : outline,
      }));
    },
    [],
  );

  const setBody = useCallback((body: string | ((b: string) => string)) => {
    setState((prev) => ({
      ...prev,
      dirty: true,
      body: typeof body === "function" ? body(prev.body) : body,
    }));
  }, []);

  const setContentDocument = useCallback(
    (doc: BlogContentDocument | ((d: BlogContentDocument) => BlogContentDocument)) => {
      setState((prev) => ({
        ...prev,
        dirty: true,
        contentDocument:
          typeof doc === "function"
            ? doc(prev.contentDocument || defaultDocument())
            : doc,
      }));
    },
    [],
  );

  const setFaqs = useCallback(
    (faqs: BlogFaqItem[] | ((f: BlogFaqItem[]) => BlogFaqItem[])) => {
      setState((prev) => ({
        ...prev,
        dirty: true,
        faqs: typeof faqs === "function" ? faqs(prev.faqs) : faqs,
      }));
    },
    [],
  );

  const beginGeneration = useCallback(
    (stage: GenerationStage, message?: string) => {
      cancelRef.current = false;
      setState((prev) => ({
        ...prev,
        generating: true,
        generationStage: stage,
        generationMessage: message || null,
        cancelGenerationRef: cancelRef,
      }));
    },
    [],
  );

  const endGeneration = useCallback(() => {
    setState((prev) => ({
      ...prev,
      generating: false,
      generationStage: "idle",
      generationMessage: null,
    }));
  }, []);

  const cancelGeneration = useCallback(() => {
    cancelRef.current = true;
    setState((prev) => ({
      ...prev,
      generationMessage: "Cancelling…",
    }));
  }, []);

  const isCancelled = useCallback(() => cancelRef.current, []);

  const setSuggestion = useCallback((s: AiSuggestionState) => {
    setState((prev) => ({ ...prev, suggestion: s }));
  }, []);

  const toggleSectionLock = useCallback((heading: string) => {
    setState((prev) => {
      const has = prev.lockedSectionHeadings.includes(heading);
      return {
        ...prev,
        lockedSectionHeadings: has
          ? prev.lockedSectionHeadings.filter((h) => h !== heading)
          : [...prev.lockedSectionHeadings, heading],
      };
    });
  }, []);

  const isSectionLocked = useCallback(
    (heading: string) => state.lockedSectionHeadings.includes(heading),
    [state.lockedSectionHeadings],
  );

  const value = useMemo(
    () => ({
      ...state,
      cancelGenerationRef: cancelRef,
      patch,
      setBrief,
      setOutline,
      setBody,
      setContentDocument,
      setFaqs,
      markDirty,
      beginGeneration,
      endGeneration,
      cancelGeneration,
      isCancelled,
      setSuggestion,
      toggleSectionLock,
      isSectionLocked,
    }),
    [
      state,
      patch,
      setBrief,
      setOutline,
      setBody,
      setContentDocument,
      setFaqs,
      markDirty,
      beginGeneration,
      endGeneration,
      cancelGeneration,
      isCancelled,
      setSuggestion,
      toggleSectionLock,
      isSectionLocked,
    ],
  );

  return (
    <BlogStudioContext.Provider value={value}>
      {children}
    </BlogStudioContext.Provider>
  );
}

export function useBlogStudio() {
  const ctx = useContext(BlogStudioContext);
  if (!ctx) {
    throw new Error("useBlogStudio must be used within BlogStudioProvider");
  }
  return ctx;
}

/** Hook alias for callers that prefer the name from the product brief. */
export function useBlogStudioState() {
  return useBlogStudio();
}
