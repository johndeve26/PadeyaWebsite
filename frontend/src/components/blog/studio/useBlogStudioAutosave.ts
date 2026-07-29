"use client";

import { useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import {
  createAdminBlogPost,
  updateAdminBlogPost,
} from "@/lib/blog-api";
import { studioAutosave } from "@/lib/blog-studio-api";

import { documentToMarkdown, isBlockDocumentMode } from "@/lib/blog-document";
import { normalizeOutline } from "./types";
import { useBlogStudio } from "./BlogStudioProvider";

export const LOCAL_DRAFT_KEY = "padeya-blog-studio-draft";

const DEBOUNCE_MS = 1600;

type StudioSnapshot = ReturnType<typeof useBlogStudio>;

type LocalDraft = {
  title: string;
  slug: string;
  excerpt: string;
  body: string;
  coverUrl: string;
  seoTitle: string;
  seoDescription: string;
  brief: unknown;
  outline: unknown;
  faqs: unknown;
  focusKeyword: string;
  secondaryKeywords: string[];
  savedAt: string;
  postId?: string | null;
};

function buildLocalDraft(studio: StudioSnapshot): LocalDraft {
  return {
    title: studio.title,
    slug: studio.slug,
    excerpt: studio.excerpt,
    body: studio.body,
    coverUrl: studio.coverUrl,
    seoTitle: studio.seoTitle,
    seoDescription: studio.seoDescription,
    brief: studio.brief,
    outline: studio.outline,
    faqs: studio.faqs,
    focusKeyword: studio.focusKeyword,
    secondaryKeywords: studio.secondaryKeywords,
    savedAt: new Date().toISOString(),
    postId: studio.postId,
  };
}

export function readLocalStudioDraft(): LocalDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(LOCAL_DRAFT_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as LocalDraft;
  } catch {
    return null;
  }
}

export function clearLocalStudioDraft() {
  try {
    localStorage.removeItem(LOCAL_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

function payloadFromStudio(studio: StudioSnapshot) {
  const blockMode = isBlockDocumentMode(
    studio.contentDocument,
    studio.contentMode,
  );
  const base = {
    title: studio.title.trim() || "Untitled draft",
    slug: studio.slug || undefined,
    excerpt: studio.excerpt,
    cover_url: studio.coverUrl || null,
    seo_title: studio.seoTitle || null,
    seo_description: studio.seoDescription || null,
    canonical_url: studio.canonicalUrl || null,
    og_image_url: studio.ogImageUrl || null,
    og_title: studio.ogTitle || null,
    social_share_text: studio.socialShareText || null,
    focus_keyword: studio.focusKeyword || null,
    secondary_keywords: studio.secondaryKeywords.length
      ? studio.secondaryKeywords
      : null,
    is_featured: studio.featured,
    category_id: studio.categoryId || null,
    author_id: studio.authorId || null,
    tag_ids: studio.tagIds,
    scheduled_at: studio.scheduledAt
      ? new Date(studio.scheduledAt).toISOString()
      : null,
    admin_notes: studio.adminNotes || null,
    studio_brief: studio.brief,
    studio_outline: normalizeOutline(studio.outline),
    faqs: studio.faqs,
    hero_settings: studio.heroSettings || null,
    editor_mode: studio.editorMode || "standard",
  };

  if (blockMode) {
    // Block mode: document is authoritative — do not send parallel body.
    return {
      ...base,
      content_document: studio.contentDocument || null,
    };
  }

  return {
    ...base,
    body: studio.body,
  };
}

/**
 * Debounced autosave with localStorage recovery, beforeunload warn,
 * and pause while AI generation is in flight (avoids race-overwrite).
 */
export function useBlogStudioAutosave(opts?: {
  enabled?: boolean;
  /** Called once after first create on /admin/blog/new */
  onCreated?: (postId: string) => void;
}) {
  const studio = useBlogStudio();
  const router = useRouter();
  const creatingRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const studioRef = useRef(studio);
  studioRef.current = studio;
  const enabled = opts?.enabled !== false;
  const onCreatedRef = useRef(opts?.onCreated);
  onCreatedRef.current = opts?.onCreated;

  const persistLocal = useCallback(() => {
    try {
      localStorage.setItem(
        LOCAL_DRAFT_KEY,
        JSON.stringify(buildLocalDraft(studioRef.current)),
      );
    } catch {
      /* quota */
    }
  }, []);

  const saveNow = useCallback(async () => {
    const current = studioRef.current;
    if (current.generating) return;
    if (!current.title.trim() && !current.body.trim()) return;

    current.patch({ autosaveStatus: "saving" });
    persistLocal();

    try {
      if (!current.postId) {
        if (creatingRef.current) return;
        creatingRef.current = true;
        const post = await createAdminBlogPost(payloadFromStudio(current));
        current.patch({
          postId: post.id,
          status: post.status,
          contentVersion:
            typeof post.content_version === "number" ? post.content_version : 1,
          dirty: false,
          autosaveStatus: "saved",
          lastSavedAt: new Date().toISOString(),
          slug: post.slug || current.slug,
        });
        clearLocalStudioDraft();
        onCreatedRef.current?.(post.id);
        router.replace(`/admin/blog/${post.id}/edit`);
        creatingRef.current = false;
        return;
      }

      try {
        const saved = await studioAutosave(current.postId, {
          ...payloadFromStudio(current),
          expected_content_version: current.contentVersion,
        });
        current.patch({
          dirty: false,
          autosaveStatus: "saved",
          lastSavedAt: new Date().toISOString(),
          contentVersion:
            typeof saved.content_version === "number"
              ? saved.content_version
              : current.contentVersion,
        });
      } catch (err) {
        // Fallback to PATCH if autosave endpoint is not yet available.
        if (err instanceof ApiError && err.status === 404) {
          const updated = await updateAdminBlogPost(
            current.postId,
            payloadFromStudio(current),
          );
          current.patch({
            dirty: false,
            autosaveStatus: "saved",
            lastSavedAt: new Date().toISOString(),
            contentVersion:
              typeof updated.content_version === "number"
                ? updated.content_version
                : current.contentVersion,
          });
        } else if (err instanceof ApiError && err.status === 409) {
          current.patch({ autosaveStatus: "conflict" });
          throw err;
        } else {
          throw err;
        }
      }
      clearLocalStudioDraft();
    } catch (err) {
      creatingRef.current = false;
      if (!(err instanceof ApiError && err.status === 409)) {
        studioRef.current.patch({ autosaveStatus: "failed" });
      }
      persistLocal();
    }
  }, [persistLocal, router]);

  useEffect(() => {
    if (!enabled || !studio.dirty || studio.generating) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      void saveNow();
    }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [
    enabled,
    studio.dirty,
    studio.generating,
    studio.title,
    studio.slug,
    studio.excerpt,
    studio.body,
    studio.contentDocument,
    studio.editorMode,
    studio.heroSettings,
    studio.coverUrl,
    studio.seoTitle,
    studio.seoDescription,
    studio.brief,
    studio.outline,
    studio.faqs,
    studio.focusKeyword,
    studio.secondaryKeywords,
    studio.categoryId,
    studio.authorId,
    studio.tagIds,
    studio.featured,
    studio.scheduledAt,
    saveNow,
  ]);

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      const current = studioRef.current;
      if (!current.dirty && current.autosaveStatus !== "failed") return;
      e.preventDefault();
      e.returnValue = "";
      persistLocal();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [persistLocal]);

  return { saveNow, persistLocal };
}
