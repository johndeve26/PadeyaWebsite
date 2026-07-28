"use client";

import { Badge, Input, Textarea } from "@/components/ui";

import type { BlogSeoScore } from "./types";
import { StudioPanel } from "./BlogStudioShell";

function Indicator({
  label,
  score,
  keyName,
}: {
  label: string;
  score: BlogSeoScore | null;
  keyName: keyof BlogSeoScore;
}) {
  const ind = score?.[keyName];
  if (!ind || typeof ind !== "object" || !("status" in ind)) return null;
  const status = (ind as { status: string; message?: string }).status;
  const message = (ind as { message?: string }).message;
  const tone =
    status === "ok" ? "success" : status === "warn" ? "warning" : "danger";
  return (
    <div className="flex items-start justify-between gap-2 text-xs">
      <div>
        <p className="font-medium text-foreground">{label}</p>
        {message ? (
          <p className="text-muted-foreground">{message}</p>
        ) : null}
      </div>
      <Badge tone={tone as "success" | "warning" | "danger"}>{status}</Badge>
    </div>
  );
}

export function BlogSeoPanel({
  slug,
  seoTitle,
  seoDescription,
  canonicalUrl,
  excerpt,
  ogTitle,
  ogImageUrl,
  socialShareText,
  focusKeyword,
  secondaryKeywords,
  slugOk,
  seoScore,
  onChange,
}: {
  slug: string;
  seoTitle: string;
  seoDescription: string;
  canonicalUrl: string;
  excerpt: string;
  ogTitle: string;
  ogImageUrl: string;
  socialShareText: string;
  focusKeyword: string;
  secondaryKeywords: string[];
  slugOk: boolean | null;
  seoScore: BlogSeoScore | null;
  onChange: (patch: Record<string, string | string[]>) => void;
}) {
  return (
    <StudioPanel
      title="SEO metadata"
      description="AI may suggest values — confirm before overwriting."
    >
      <div className="space-y-3">
        <Input
          label="Slug"
          value={slug}
          onChange={(e) => onChange({ slug: e.target.value })}
          hint={
            slugOk === null
              ? undefined
              : slugOk
                ? "Slug available"
                : "Slug already taken"
          }
        />
        <Input
          label="Meta title"
          value={seoTitle}
          onChange={(e) => onChange({ seoTitle: e.target.value })}
        />
        <Textarea
          label="Meta description"
          rows={2}
          value={seoDescription}
          onChange={(e) => onChange({ seoDescription: e.target.value })}
        />
        <Input
          label="Canonical URL"
          value={canonicalUrl}
          onChange={(e) => onChange({ canonicalUrl: e.target.value })}
        />
        <Textarea
          label="Excerpt"
          rows={2}
          value={excerpt}
          onChange={(e) => onChange({ excerpt: e.target.value })}
        />
        <Input
          label="OG title"
          value={ogTitle}
          onChange={(e) => onChange({ ogTitle: e.target.value })}
        />
        <Input
          label="OG image URL"
          value={ogImageUrl}
          onChange={(e) => onChange({ ogImageUrl: e.target.value })}
        />
        <Textarea
          label="Social share text"
          rows={2}
          value={socialShareText}
          onChange={(e) => onChange({ socialShareText: e.target.value })}
        />
        <Input
          label="Focus keyword"
          value={focusKeyword}
          onChange={(e) => onChange({ focusKeyword: e.target.value })}
        />
        <Textarea
          label="Secondary keywords (one per line)"
          rows={2}
          value={secondaryKeywords.join("\n")}
          onChange={(e) =>
            onChange({
              secondaryKeywords: e.target.value
                .split("\n")
                .map((s) => s.trim())
                .filter(Boolean),
            })
          }
        />
        <div className="space-y-2 border-t border-border pt-3">
          <p className="text-xs font-semibold text-foreground">Validation</p>
          <Indicator label="Title length" score={seoScore} keyName="title_length" />
          <Indicator
            label="Meta title"
            score={seoScore}
            keyName="meta_title_length"
          />
          <Indicator
            label="Description"
            score={seoScore}
            keyName="description_length"
          />
          <Indicator
            label="Keyword in title"
            score={seoScore}
            keyName="keyword_in_title"
          />
          <Indicator
            label="Keyword in intro"
            score={seoScore}
            keyName="keyword_in_intro"
          />
          <Indicator
            label="Keyword in headings"
            score={seoScore}
            keyName="keyword_in_headings"
          />
          <Indicator label="Slug quality" score={seoScore} keyName="slug_quality" />
          <Indicator
            label="Heading hierarchy"
            score={seoScore}
            keyName="heading_hierarchy"
          />
          <Indicator
            label="Article length"
            score={seoScore}
            keyName="article_length"
          />
          <Indicator
            label="Internal links"
            score={seoScore}
            keyName="internal_links"
          />
          <Indicator label="Image alt" score={seoScore} keyName="image_alt" />
        </div>
      </div>
    </StudioPanel>
  );
}
