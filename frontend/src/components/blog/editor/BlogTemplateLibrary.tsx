"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui";
import { fetchLayoutTemplates } from "@/lib/blog-document-api";
import { cloneDocument, type BlogContentDocument, type LayoutTemplate } from "@/lib/blog-document";

type Props = {
  onApply: (document: BlogContentDocument) => void;
};

export function BlogTemplateLibrary({ onApply }: Props) {
  const [templates, setTemplates] = useState<LayoutTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLayoutTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="p-4 text-sm text-muted-foreground">Loading templates…</p>;

  return (
    <div className="p-3 space-y-3">
      <h3 className="font-medium text-sm text-foreground">Templates</h3>
      <div className="space-y-2">
        {templates.map((t) => (
          <div
            key={t.slug}
            className="rounded-[var(--radius-md)] border border-border bg-card p-3 text-card-foreground shadow-[var(--shadow-soft)] transition-colors hover:border-primary/50 dark:bg-surface-elevated dark:hover:bg-surface-inset"
          >
            <p className="font-medium text-sm text-foreground">{t.name}</p>
            {t.description ? (
              <p className="text-xs text-muted-foreground mt-1">{t.description}</p>
            ) : null}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="mt-2"
              onClick={() => {
                if (
                  window.confirm(
                    `Apply template "${t.name}"? This replaces the current layout structure.`,
                  )
                ) {
                  onApply(cloneDocument(t.document));
                }
              }}
            >
              Use template
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
