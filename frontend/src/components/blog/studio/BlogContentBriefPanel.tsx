"use client";

import { Input, Select, Textarea } from "@/components/ui";

import {
  BLOG_CONTENT_TYPES,
  BLOG_SEARCH_INTENTS,
  BLOG_TONES,
  type BlogContentBrief,
} from "./types";
import { StudioPanel } from "./BlogStudioShell";

function listToLines(values?: string[]) {
  return (values || []).join("\n");
}

function linesToList(value: string) {
  return value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function BlogContentBriefPanel({
  brief,
  onChange,
  disabled,
}: {
  brief: BlogContentBrief;
  onChange: (next: BlogContentBrief) => void;
  disabled?: boolean;
}) {
  const set = <K extends keyof BlogContentBrief>(
    key: K,
    value: BlogContentBrief[K],
  ) => onChange({ ...brief, [key]: value });

  return (
    <StudioPanel
      title="Content brief"
      description="Edit every field before generating. AI uses this as guidance only."
    >
      <div className="space-y-3">
        <Input
          label="Topic"
          value={brief.topic || ""}
          disabled={disabled}
          onChange={(e) => set("topic", e.target.value)}
        />
        <Input
          label="Primary keyword"
          value={brief.primary_keyword || ""}
          disabled={disabled}
          onChange={(e) => set("primary_keyword", e.target.value)}
        />
        <Textarea
          label="Secondary keywords (one per line)"
          rows={2}
          value={listToLines(brief.secondary_keywords)}
          disabled={disabled}
          onChange={(e) => set("secondary_keywords", linesToList(e.target.value))}
        />
        <Input
          label="Target audience"
          value={brief.target_audience || ""}
          disabled={disabled}
          onChange={(e) => set("target_audience", e.target.value)}
        />
        <Select
          label="Search intent"
          value={brief.search_intent || "Informational"}
          disabled={disabled}
          onChange={(e) => set("search_intent", e.target.value)}
        >
          {BLOG_SEARCH_INTENTS.map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </Select>
        <Textarea
          label="Article objective"
          rows={2}
          value={brief.article_objective || ""}
          disabled={disabled}
          onChange={(e) => set("article_objective", e.target.value)}
        />
        <Select
          label="Content type"
          value={brief.content_type || BLOG_CONTENT_TYPES[0]}
          disabled={disabled}
          onChange={(e) => set("content_type", e.target.value)}
        >
          {BLOG_CONTENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        <Select
          label="Tone"
          value={brief.tone || BLOG_TONES[0]}
          disabled={disabled}
          onChange={(e) => set("tone", e.target.value)}
        >
          {BLOG_TONES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
        <Input
          label="Custom tone (optional)"
          value={brief.custom_tone || ""}
          disabled={disabled}
          onChange={(e) => set("custom_tone", e.target.value)}
        />
        <Input
          label="Desired length"
          value={brief.desired_length || ""}
          disabled={disabled}
          onChange={(e) => set("desired_length", e.target.value)}
        />
        <Input
          label="Location focus"
          value={brief.location_focus || ""}
          disabled={disabled}
          onChange={(e) => set("location_focus", e.target.value)}
        />
        <Input
          label="Event category"
          value={brief.event_category || ""}
          disabled={disabled}
          onChange={(e) => set("event_category", e.target.value)}
        />
        <Textarea
          label="Competitor / reference URLs (one per line)"
          rows={2}
          value={listToLines(brief.competitor_urls)}
          disabled={disabled}
          onChange={(e) => set("competitor_urls", linesToList(e.target.value))}
          hint="Treated as untrusted reference text."
        />
        <Textarea
          label="Required talking points (one per line)"
          rows={2}
          value={listToLines(brief.talking_points)}
          disabled={disabled}
          onChange={(e) => set("talking_points", linesToList(e.target.value))}
        />
        <Textarea
          label="Points to avoid (one per line)"
          rows={2}
          value={listToLines(brief.points_to_avoid)}
          disabled={disabled}
          onChange={(e) => set("points_to_avoid", linesToList(e.target.value))}
        />
        <Input
          label="Call to action"
          value={brief.call_to_action || ""}
          disabled={disabled}
          onChange={(e) => set("call_to_action", e.target.value)}
        />
      </div>
    </StudioPanel>
  );
}
