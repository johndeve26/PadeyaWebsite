"use client";

import { Button, Input, Switch, Textarea } from "@/components/ui";

import type { BlogOutline, BlogOutlineSection } from "./types";
import { newSectionId } from "./types";
import { StudioPanel } from "./BlogStudioShell";

export function BlogOutlineEditor({
  outline,
  onChange,
  onRegenerateAll,
  onRegenerateSection,
  busy,
}: {
  outline: BlogOutline;
  onChange: (next: BlogOutline) => void;
  onRegenerateAll: () => void;
  onRegenerateSection: (sectionId: string) => void;
  busy?: boolean;
}) {
  const sections = outline.sections || [];

  function updateSection(id: string, patch: Partial<BlogOutlineSection>) {
    onChange({
      ...outline,
      sections: sections.map((s) => (s.id === id ? { ...s, ...patch } : s)),
    });
  }

  function move(id: string, dir: -1 | 1) {
    const idx = sections.findIndex((s) => s.id === id);
    const to = idx + dir;
    if (idx < 0 || to < 0 || to >= sections.length) return;
    const next = [...sections];
    const tmp = next[idx];
    next[idx] = next[to];
    next[to] = tmp;
    onChange({ ...outline, sections: next });
  }

  function remove(id: string) {
    onChange({
      ...outline,
      sections: sections.filter((s) => s.id !== id),
    });
  }

  function add() {
    onChange({
      ...outline,
      sections: [
        ...sections,
        {
          id: newSectionId(),
          heading: "New section",
          level: 2,
          key_point: "",
          locked: false,
        },
      ],
    });
  }

  return (
    <StudioPanel
      title="Outline editor"
      description="Approve the outline before full-draft generation."
      actions={
        <div className="flex flex-wrap gap-1">
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={onRegenerateAll}
          >
            Regenerate
          </Button>
          <Button size="sm" variant="ghost" disabled={busy} onClick={add}>
            Add
          </Button>
        </div>
      }
    >
      <Textarea
        label="Introduction purpose"
        rows={2}
        value={outline.introduction_purpose || ""}
        onChange={(e) =>
          onChange({ ...outline, introduction_purpose: e.target.value })
        }
      />
      <ul className="mt-3 space-y-3">
        {sections.map((sec, i) => (
          <li
            key={sec.id}
            className="space-y-2 rounded-[var(--radius-sm)] border border-border bg-surface-muted/40 p-2"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-semibold text-muted-foreground">
                Section {i + 1}
              </span>
              <Switch
                checked={Boolean(sec.locked)}
                onCheckedChange={(v) => updateSection(sec.id, { locked: v })}
                label="Lock"
              />
            </div>
            <Input
              label="Heading"
              value={sec.heading}
              onChange={(e) => updateSection(sec.id, { heading: e.target.value })}
            />
            <Textarea
              label="Key point"
              rows={2}
              value={sec.key_point || ""}
              onChange={(e) =>
                updateSection(sec.id, { key_point: e.target.value })
              }
            />
            <div className="flex flex-wrap gap-1">
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || i === 0}
                onClick={() => move(sec.id, -1)}
              >
                Up
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || i === sections.length - 1}
                onClick={() => move(sec.id, 1)}
              >
                Down
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={busy || sec.locked}
                onClick={() => onRegenerateSection(sec.id)}
              >
                Regenerate
              </Button>
              <Button
                size="sm"
                variant="danger"
                disabled={busy}
                onClick={() => remove(sec.id)}
              >
                Remove
              </Button>
            </div>
          </li>
        ))}
      </ul>
      <Textarea
        label="Conclusion direction"
        className="mt-3"
        rows={2}
        value={outline.conclusion_direction || ""}
        onChange={(e) =>
          onChange({ ...outline, conclusion_direction: e.target.value })
        }
      />
      <div className="mt-3">
        <Switch
          checked={Boolean(outline.approved)}
          onCheckedChange={(v) => onChange({ ...outline, approved: v })}
          label="Outline approved"
        />
      </div>
    </StudioPanel>
  );
}
