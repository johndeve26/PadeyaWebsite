"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui";
import { createAdminBlogPost, type BlogPost } from "@/lib/blog-api";
import { cloneDocument, type BlogContentDocument } from "@/lib/blog-document";
import { fetchLayoutTemplates, patchBlogDocument } from "@/lib/blog-document-api";
import type { LayoutTemplate } from "@/lib/blog-document";

type Step = "choose" | "template";

export function BlogCreationStart() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("choose");
  const [busy, setBusy] = useState(false);
  const [templates, setTemplates] = useState<LayoutTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);

  useEffect(() => {
    if (step !== "template") return;
    setTemplatesLoading(true);
    fetchLayoutTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setTemplatesLoading(false));
  }, [step]);

  async function createAndGo(tab: "write" | "plan", document?: BlogContentDocument) {
    if (busy) return;
    setBusy(true);
    try {
      const post = await createAdminBlogPost({
        title: "Untitled post",
        status: "draft",
      });
      if (document) {
        const version = post.content_version ?? 1;
        await patchBlogDocument(post.id, {
          content_document: document,
          editor_mode: "standard",
          expected_content_version: version,
        });
      }
      router.push(`/admin/blog/${post.id}/edit?tab=${tab}`);
    } catch {
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

          {templatesLoading ? (
            <p className="text-center text-sm text-muted-foreground">Loading templates…</p>
          ) : (
            <ul className="max-h-[min(24rem,60vh)] space-y-2 overflow-y-auto">
              {templates.map((t) => (
                <li key={t.slug}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      void createAndGo("write", cloneDocument(t.document))
                    }
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
              onClick={() => setStep("choose")}
            >
              Back
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
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

        <div className="grid gap-4 sm:grid-cols-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => void createAndGo("write")}
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
            onClick={() => void createAndGo("plan")}
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
