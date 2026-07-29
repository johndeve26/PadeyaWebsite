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

  if (loading) return <p className="p-4 text-sm text-muted">Loading templates…</p>;

  return (
    <div className="p-4 space-y-3">
      <h3 className="font-medium text-sm">Templates</h3>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {templates.map((t) => (
          <div
            key={t.slug}
            className="rounded-[var(--radius-md)] border border-border p-3 hover:border-primary/40"
          >
            <p className="font-medium text-sm">{t.name}</p>
            {t.description ? (
              <p className="text-xs text-muted mt-1">{t.description}</p>
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
