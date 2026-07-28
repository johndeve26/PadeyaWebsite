"use client";

import { Alert, Button, Input, Textarea } from "@/components/ui";

import type { BlogImagePrompt } from "./types";
import { StudioPanel } from "./BlogStudioShell";

function looksLikeSvg(url: string) {
  const lower = url.trim().toLowerCase();
  return (
    lower.endsWith(".svg") ||
    lower.includes("image/svg") ||
    lower.includes("data:image/svg")
  );
}

export function BlogImageAssistant({
  coverUrl,
  imagePrompt,
  busy,
  onCoverChange,
  onGenerate,
  onApplyAltCaption,
}: {
  coverUrl: string;
  imagePrompt: BlogImagePrompt | null;
  busy?: boolean;
  onCoverChange: (url: string) => void;
  onGenerate: () => void;
  onApplyAltCaption?: (alt: string, caption: string) => void;
}) {
  const svgRejected = Boolean(coverUrl && looksLikeSvg(coverUrl));

  return (
    <StudioPanel
      title="Featured image assistant"
      description="Generates prompts, alt text, and captions only — does not auto-upload or invent assets."
      actions={
        <Button size="sm" variant="secondary" disabled={busy} onClick={onGenerate}>
          {busy ? "Generating…" : "Generate prompt"}
        </Button>
      }
    >
      <Input
        label="Cover image URL"
        value={coverUrl}
        onChange={(e) => onCoverChange(e.target.value)}
        hint="Raster images only (JPEG, PNG, WebP, GIF)."
      />
      {svgRejected ? (
        <Alert tone="danger" title="SVG rejected">
          SVG cover URLs are not allowed. Use a raster image URL instead.
        </Alert>
      ) : null}
      {imagePrompt ? (
        <div className="mt-3 space-y-2">
          {imagePrompt.concept ? (
            <p className="text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">Concept: </span>
              {imagePrompt.concept}
            </p>
          ) : null}
          <Textarea
            label="Image prompt"
            rows={3}
            readOnly
            value={imagePrompt.prompt || ""}
          />
          <Input label="Alt text" readOnly value={imagePrompt.alt_text || ""} />
          <Input label="Caption" readOnly value={imagePrompt.caption || ""} />
          {imagePrompt.aspect_ratio ? (
            <p className="text-[11px] text-muted-foreground">
              Aspect: {imagePrompt.aspect_ratio}
              {imagePrompt.focal_point
                ? ` · Focal: ${imagePrompt.focal_point}`
                : ""}
            </p>
          ) : null}
          {onApplyAltCaption && (imagePrompt.alt_text || imagePrompt.caption) ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                onApplyAltCaption(
                  imagePrompt.alt_text || "",
                  imagePrompt.caption || "",
                )
              }
            >
              Copy alt into notes
            </Button>
          ) : null}
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">
          No prompt yet. Generate after the title and brief are set.
        </p>
      )}
    </StudioPanel>
  );
}
