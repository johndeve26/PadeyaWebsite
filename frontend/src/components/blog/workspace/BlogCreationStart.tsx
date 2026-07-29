"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Alert, Button } from "@/components/ui";
import { createAdminBlogPost, fetchAdminBlogPost } from "@/lib/blog-api";
import { cloneDocument, type BlogContentDocument } from "@/lib/blog-document";
import { fetchLayoutTemplates, patchBlogDocument } from "@/lib/blog-document-api";
import type { LayoutTemplate } from "@/lib/blog-document";
import {
  clearCreationResult,
  clearPendingTemplate,
  newCreationKey,
  readCreationResult,
  readPendingTemplate,
  writeCreationResult,
  writePendingTemplate,
} from "@/lib/blog-creation";

type Step = "choose" | "template";

export function BlogCreationStart() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("choose");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<LayoutTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [creationKey, setCreationKey] = useState(() => newCreationKey());

  useEffect(() => {
    const pending = readPendingTemplate();
    if (!pending) return;
    void recoverPendingTemplate(pending);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (step !== "template") return;
    setTemplatesLoading(true);
    fetchLayoutTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setTemplatesLoading(false));
  }, [step]);

  async function applyTemplateToPost(
    postId: string,
    contentVersion: number,
    document: BlogContentDocument,
  ) {
    await patchBlogDocument(postId, {
      content_document: document,
      editor_mode: "standard",
      expected_content_version: contentVersion,
    });
  }

  async function recoverPendingTemplate(pending: NonNullable<ReturnType<typeof readPendingTemplate>>) {
    setBusy(true);
    setError(null);
    try {
      const [post, templates] = await Promise.all([
        fetchAdminBlogPost(pending.postId),
        fetchLayoutTemplates(),
      ]);
      const template = templates.find((t) => t.slug === pending.templateSlug);
      if (!template) {
        throw new Error("Template not found");
      }
      await applyTemplateToPost(
        pending.postId,
        post.content_version ?? 1,
        cloneDocument(template.document),
      );
      clearPendingTemplate();
      clearCreationResult(pending.creationKey);
      router.push(`/admin/blog/${pending.postId}/edit?tab=${pending.tab}`);
    } catch {
      setError("Template application failed. Retry below — we will not create another draft.");
      setStep("template");
      setBusy(false);
    }
  }

  async function ensureDraft(): Promise<{ id: string; content_version: number }> {
    const existingId = readCreationResult(creationKey);
    if (existingId) {
      const post = await fetchAdminBlogPost(existingId);
      return { id: post.id, content_version: post.content_version ?? 1 };
    }
    const post = await createAdminBlogPost({
      title: `Untitled post ${creationKey.slice(0, 8)}`,
      client_creation_id: creationKey,
    });
    writeCreationResult(creationKey, post.id);
    return { id: post.id, content_version: post.content_version ?? 1 };
  }

  async function startBlankOrAi(choice: "blank" | "ai") {
    if (busy) return;
    setBusy(true);
    setError(null);
    const tab = choice === "ai" ? "plan" : "write";
    try {
      const post = await ensureDraft();
      clearPendingTemplate();
      router.push(`/admin/blog/${post.id}/edit?tab=${tab}`);
    } catch {
      setError("Could not create draft. Please try again.");
      setCreationKey(newCreationKey());
      setBusy(false);
    }
  }

  async function applyTemplateChoice(template: LayoutTemplate) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const post = await ensureDraft();
      writePendingTemplate({
        postId: post.id,
        templateSlug: template.slug,
        tab: "write",
        creationKey,
        createdAt: new Date().toISOString(),
      });
      await applyTemplateToPost(
        post.id,
        post.content_version,
        cloneDocument(template.document),
      );
      clearPendingTemplate();
      router.push(`/admin/blog/${post.id}/edit?tab=write`);
    } catch {
      setError(
        "Draft was created but the template could not be applied. Open the draft and retry from Design → Templates.",
      );
      const existingId = readCreationResult(creationKey);
      if (existingId) {
        router.push(`/admin/blog/${existingId}/edit?tab=design`);
        return;
      }
      setBusy(false);
    }
  }

  if (step === "template") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="w-full max-w-xl space-y-6">
          <div className="space-y-2 text-center">
            <h1 className="text-2xl font-bold text-foreground">Choose a template</h1>
            <p className="text-sm text-muted-foreground">
              Pick a structure to start from — you can edit everything after.
            </p>
          </div>

          {error ? (
            <Alert tone="danger" title="Template application">
              {error}
            </Alert>
          ) : null}

          {templatesLoading ? (
            <p className="text-center text-sm text-muted-foreground">Loading templates…</p>
          ) : (
            <ul className="max-h-[min(24rem,60vh)] space-y-2 overflow-y-auto">
              {templates.map((t) => (
                <li key={t.slug}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void applyTemplateChoice(t)}
                    className="w-full rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-primary disabled:opacity-60"
                  >
                    <p className="font-semibold text-foreground">{t.name}</p>
                    {t.description ? (
                      <p className="mt-1 text-sm text-muted-foreground">{t.description}</p>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex justify-center gap-3">
            <Button
              type="button"
              variant="secondary"
              disabled={busy}
              onClick={() => {
                setError(null);
                setStep("choose");
              }}
            >
              Back
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6" data-testid="blog-creation-start">
      <div className="w-full max-w-2xl space-y-8">
        <div className="space-y-2 text-center">
          <h1 className="font-display text-2xl font-bold text-foreground">
            Create a blog article
          </h1>
          <p className="text-sm text-muted-foreground">
            Write manually, start from a template, or use optional AI — you&apos;ll always
            land in the editor.
          </p>
        </div>

        {error ? (
          <Alert tone="danger" title="Could not start">
            {error}
          </Alert>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => void startBlankOrAi("blank")}
            className="rounded-xl border border-border bg-card p-5 text-left transition-colors hover:border-primary disabled:opacity-60"
          >
            <p className="font-semibold text-foreground">Start blank</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Write and design everything manually.
            </p>
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => setStep("template")}
            className="rounded-xl border border-border bg-card p-5 text-left transition-colors hover:border-primary disabled:opacity-60"
          >
            <p className="font-semibold text-foreground">Use a template</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Choose an editable article structure.
            </p>
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => void startBlankOrAi("ai")}
            className="rounded-xl border border-border bg-card p-5 text-left transition-colors hover:border-primary disabled:opacity-60"
          >
            <p className="font-semibold text-foreground">Create with AI</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Plan with AI, then edit everything manually.
            </p>
          </button>
        </div>

        {busy ? (
          <p className="text-center text-sm text-muted-foreground">Creating draft…</p>
        ) : null}

        <p className="text-center text-xs text-muted-foreground">
          All choices create one draft — nothing publishes automatically.
        </p>
      </div>
    </div>
  );
}
