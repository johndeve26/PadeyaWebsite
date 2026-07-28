"use client";

import { Button, Input, Textarea } from "@/components/ui";

import type { BlogFaqItem } from "./types";
import { newFaqId } from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function BlogFaqEditor({
  faqs,
  onChange,
  busy,
  onGenerate,
}: {
  faqs: BlogFaqItem[];
  onChange: (faqs: BlogFaqItem[]) => void;
  busy?: boolean;
  onGenerate: () => void;
}) {
  function update(id: string, patch: Partial<BlogFaqItem>) {
    onChange(faqs.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  }

  return (
    <StudioPanel
      title="FAQs"
      description="Editable FAQ block for the article."
      actions={
        <div className="flex gap-1">
          <Button size="sm" variant="secondary" disabled={busy} onClick={onGenerate}>
            {busy ? "Generating…" : "Generate"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              onChange([
                ...faqs,
                { id: newFaqId(), question: "", answer: "" },
              ])
            }
          >
            Add
          </Button>
        </div>
      }
    >
      {faqs.length === 0 ? (
        <p className="text-xs text-muted-foreground">No FAQs yet.</p>
      ) : (
        <ul className="space-y-3">
          {faqs.map((faq, i) => (
            <li
              key={faq.id}
              className="space-y-2 rounded-[var(--radius-sm)] border border-border p-2"
            >
              <Input
                label={`Question ${i + 1}`}
                value={faq.question}
                onChange={(e) => update(faq.id, { question: e.target.value })}
              />
              <Textarea
                label="Answer"
                rows={2}
                value={faq.answer}
                onChange={(e) => update(faq.id, { answer: e.target.value })}
              />
              <Button
                size="sm"
                variant="danger"
                onClick={() => onChange(faqs.filter((f) => f.id !== faq.id))}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
    </StudioPanel>
  );
}
