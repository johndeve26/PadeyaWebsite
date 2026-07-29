"use client";

import { Button } from "@/components/ui";
import { cloneDocument, defaultDocument, type BlogContentDocument } from "@/lib/blog-document";
import { fetchLayoutTemplates } from "@/lib/blog-document-api";

export type CreationChoice = "blank" | "template" | "ai";

type Props = {
  onContinue: (choice: CreationChoice, document?: BlogContentDocument) => void;
};

export function BlogCreationEntry({ onContinue }: Props) {
  const handleTemplate = async () => {
    try {
      const templates = await fetchLayoutTemplates();
      const howTo = templates.find((t) => t.slug === "how-to-guide") || templates[1];
      if (howTo) {
        onContinue("template", cloneDocument(howTo.document));
      } else {
        onContinue("template", defaultDocument());
      }
    } catch {
      onContinue("template", defaultDocument());
    }
  };

  return (
    <div className="mx-auto max-w-2xl py-16 px-4 space-y-8">
      <div className="text-center space-y-2">
        <h1 className="font-display text-2xl font-bold">Create a blog article</h1>
        <p className="text-muted-foreground">
          Write manually, start from a template, or use optional AI — you&apos;ll always land in the editor.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <button
          type="button"
          className="rounded-[var(--radius-md)] border border-border bg-surface p-6 text-left hover:border-primary transition-colors"
          onClick={() => onContinue("blank", defaultDocument())}
        >
          <p className="font-semibold">Start blank</p>
          <p className="text-sm text-muted-foreground mt-2">
            Write and design the article manually.
          </p>
        </button>

        <button
          type="button"
          className="rounded-[var(--radius-md)] border border-border bg-surface p-6 text-left hover:border-primary transition-colors"
          onClick={() => void handleTemplate()}
        >
          <p className="font-semibold">Use a template</p>
          <p className="text-sm text-muted-foreground mt-2">
            Begin with a predefined article structure.
          </p>
        </button>

        <button
          type="button"
          className="rounded-[var(--radius-md)] border border-border bg-surface p-6 text-left hover:border-primary transition-colors"
          onClick={() => onContinue("ai", defaultDocument())}
        >
          <p className="font-semibold">Create with AI</p>
          <p className="text-sm text-muted-foreground mt-2">
            Generate a brief, outline, or initial draft — optional.
          </p>
        </button>
      </div>

      <p className="text-center text-xs text-muted-foreground">
        AI assists only when you ask. Nothing publishes without your confirmation.
      </p>
    </div>
  );
}
