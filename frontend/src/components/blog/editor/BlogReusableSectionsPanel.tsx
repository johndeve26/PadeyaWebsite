"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui";
import { fetchReusableSections } from "@/lib/blog-document-api";
import {
  cloneBlockTree,
  insertBlockAtRoot,
  type BlogContentDocument,
  type ReusableSection,
} from "@/lib/blog-document";

type Props = {
  document: BlogContentDocument;
  onChange: (doc: BlogContentDocument) => void;
};

export function BlogReusableSectionsPanel({ document, onChange }: Props) {
  const [sections, setSections] = useState<ReusableSection[]>([]);

  useEffect(() => {
    fetchReusableSections().then(setSections).catch(() => setSections([]));
  }, []);

  return (
    <div className="p-4 space-y-3">
      <h3 className="font-medium text-sm">Reusable sections</h3>
      <p className="text-xs text-muted">Inserted sections are copied — template changes won&apos;t affect this post.</p>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {sections.map((s) => (
          <div key={s.slug} className="border border-border rounded-[var(--radius-md)] p-2">
            <p className="text-sm font-medium">{s.name}</p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-1"
              onClick={() => {
                const copied = cloneBlockTree(s.section);
                onChange({
                  ...document,
                  blocks: insertBlockAtRoot(document.blocks, copied),
                });
              }}
            >
              Insert
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
