"use client";

import { useId, useRef, useState } from "react";

import { Alert, Button, Input, Media } from "@/components/ui";
import { ApiError, apiRequest, apiUpload } from "@/lib/api";
import { cn } from "@/lib/cn";
import { openPublicMediaInNewTab } from "@/lib/media-preview";

export type TaxonomyImageKind = "category" | "city" | "state" | "area";

export type TaxonomyVisualFields = {
  primary_image_url?: string | null;
  primary_image_alt?: string | null;
  primary_image_focal_x?: number | null;
  primary_image_focal_y?: number | null;
  hero_image_url?: string | null;
  hero_image_alt?: string | null;
  hero_image_focal_x?: number | null;
  hero_image_focal_y?: number | null;
};

const ACCEPT = "image/jpeg,image/png,image/webp,image/gif";
const MAX_MB = 5;

function pct(n: number | null | undefined) {
  const v = typeof n === "number" && Number.isFinite(n) ? n : 0.5;
  return `${Math.round(Math.min(1, Math.max(0, v)) * 100)}%`;
}

function PreviewFrame({
  label,
  url,
  alt,
  focalX,
  focalY,
  wide,
}: {
  label: string;
  url?: string | null;
  alt: string;
  focalX?: number | null;
  focalY?: number | null;
  wide?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-muted-foreground">{label}</p>
      <div
        className={cn(
          "relative overflow-hidden rounded-[var(--radius-md)] border border-border bg-ink",
          wide ? "aspect-[21/9]" : "aspect-[16/11]",
        )}
      >
        {url ? (
          <Media
            src={url}
            alt={alt}
            className="absolute inset-0 h-full w-full object-cover"
            style={{
              objectPosition: `${pct(focalX)} ${pct(focalY)}`,
            }}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-paper/70">
            Branded fallback
          </div>
        )}
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-ink/80 via-ink/20 to-transparent"
        />
        <div className="absolute inset-x-0 bottom-0 p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-accent">
            Preview
          </p>
          <p className="text-sm font-extrabold text-paper">{alt || "Term"}</p>
        </div>
      </div>
    </div>
  );
}

export function TaxonomyVisualsEditor({
  kind,
  termId,
  termName,
  value,
  onChange,
  disabled = false,
}: {
  kind: TaxonomyImageKind;
  termId: string;
  termName: string;
  value: TaxonomyVisualFields;
  onChange: (next: TaxonomyVisualFields) => void;
  disabled?: boolean;
}) {
  const inputId = useId();
  const fileRef = useRef<HTMLInputElement>(null);
  const [role, setRole] = useState<"primary" | "hero">("primary");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const primaryUrl = value.primary_image_url || "";
  const heroUrl = value.hero_image_url || primaryUrl;

  async function upload(file: File) {
    if (busy || disabled) return;
    setBusy(true);
    setError(null);
    setStatus("Uploading…");
    const previous = { ...value };
    try {
      const qs = new URLSearchParams({
        kind,
        term_id: termId,
        image_role: role,
        apply: "true",
      });
      if (value.primary_image_alt && role === "primary") {
        qs.set("alt", value.primary_image_alt);
      }
      if (value.hero_image_alt && role === "hero") {
        qs.set("alt", value.hero_image_alt);
      }
      const form = new FormData();
      form.append("file", file);
      const res = await apiUpload<{ url: string }>(
        `/taxonomy/admin/media/upload?${qs}`,
        form,
      );
      const next =
        role === "hero"
          ? { ...value, hero_image_url: res.url }
          : { ...value, primary_image_url: res.url };
      onChange(next);
      setStatus("Uploaded — saved");
    } catch (err) {
      onChange(previous);
      setError(err instanceof ApiError ? err.detail : "Upload failed");
      setStatus(null);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function saveVisuals(patch: TaxonomyVisualFields & { clear_primary?: boolean; clear_hero?: boolean }) {
    setBusy(true);
    setError(null);
    try {
      const path =
        kind === "category"
          ? `/taxonomy/admin/categories/${termId}/visuals`
          : `/taxonomy/admin/locations/${termId}/visuals`;
      const updated = await apiRequest<TaxonomyVisualFields>(path, {
        method: "PATCH",
        body: patch,
      });
      onChange({
        primary_image_url: updated.primary_image_url,
        primary_image_alt: updated.primary_image_alt,
        primary_image_focal_x: updated.primary_image_focal_x,
        primary_image_focal_y: updated.primary_image_focal_y,
        hero_image_url: updated.hero_image_url,
        hero_image_alt: updated.hero_image_alt,
        hero_image_focal_x: updated.hero_image_focal_x,
        hero_image_focal_y: updated.hero_image_focal_y,
      });
      setStatus("Visuals saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  function setFocal(clientX: number, clientY: number, el: HTMLElement) {
    const rect = el.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    const y = Math.min(1, Math.max(0, (clientY - rect.top) / rect.height));
    if (role === "hero") {
      onChange({ ...value, hero_image_focal_x: x, hero_image_focal_y: y });
    } else {
      onChange({ ...value, primary_image_focal_x: x, primary_image_focal_y: y });
    }
  }

  const activeUrl = role === "hero" ? value.hero_image_url : value.primary_image_url;
  const fx =
    role === "hero" ? value.hero_image_focal_x : value.primary_image_focal_x;
  const fy =
    role === "hero" ? value.hero_image_focal_y : value.primary_image_focal_y;

  return (
    <section className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-surface-inset/40 p-4">
      <div>
        <h3 className="text-sm font-bold tracking-tight">Visuals</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          JPEG, PNG, WebP, or GIF · max {MAX_MB}MB · SVG rejected. Unique object
          keys on every upload (CDN-safe replace).{" "}
          <strong className="font-semibold text-foreground">Primary</strong> shows
          on category/city cards;{" "}
          <strong className="font-semibold text-foreground">Hero</strong> is for
          hub headers (falls back to primary when empty).
        </p>
      </div>

      {error ? <Alert tone="danger">{error}</Alert> : null}
      {status ? (
        <p className="text-xs font-medium text-muted-foreground" aria-live="polite">
          {status}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant={role === "primary" ? "primary" : "secondary"}
          onClick={() => setRole("primary")}
          disabled={busy || disabled}
        >
          Primary (cards)
        </Button>
        <Button
          type="button"
          size="sm"
          variant={role === "hero" ? "primary" : "secondary"}
          onClick={() => setRole("hero")}
          disabled={busy || disabled}
        >
          Hero (hub)
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <PreviewFrame
          label="Card preview"
          url={primaryUrl}
          alt={value.primary_image_alt || termName}
          focalX={value.primary_image_focal_x}
          focalY={value.primary_image_focal_y}
        />
        <PreviewFrame
          label="Hero preview"
          url={heroUrl}
          alt={value.hero_image_alt || value.primary_image_alt || termName}
          focalX={value.hero_image_focal_x ?? value.primary_image_focal_x}
          focalY={value.hero_image_focal_y ?? value.primary_image_focal_y}
          wide
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          id={inputId}
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          disabled={busy || disabled}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void upload(file);
          }}
        />
        <Button
          type="button"
          size="sm"
          disabled={busy || disabled}
          onClick={() => fileRef.current?.click()}
        >
          {activeUrl ? "Replace image" : "Upload image"}
        </Button>
        {activeUrl ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={busy || disabled}
            onClick={() =>
              void saveVisuals(
                role === "hero" ? { clear_hero: true } : { clear_primary: true },
              )
            }
          >
            Remove {role}
          </Button>
        ) : null}
        {activeUrl ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => openPublicMediaInNewTab(activeUrl)}
          >
            Open preview
          </Button>
        ) : null}
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy || disabled}
          onClick={() => {
            if (role === "hero") {
              onChange({
                ...value,
                hero_image_focal_x: 0.5,
                hero_image_focal_y: 0.5,
              });
            } else {
              onChange({
                ...value,
                primary_image_focal_x: 0.5,
                primary_image_focal_y: 0.5,
              });
            }
          }}
        >
          Reset focus
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy || disabled}
          onClick={() => void saveVisuals(value)}
        >
          Save visuals
        </Button>
      </div>

      <Input
        label={role === "hero" ? "Hero alt text" : "Primary alt text"}
        value={
          (role === "hero" ? value.hero_image_alt : value.primary_image_alt) || ""
        }
        onChange={(e) => {
          const v = e.target.value;
          onChange(
            role === "hero"
              ? { ...value, hero_image_alt: v }
              : { ...value, primary_image_alt: v },
          );
        }}
        disabled={busy || disabled}
        hint="Describes the image for accessibility. Empty uses the term name."
      />

      <div className="space-y-2">
        <p className="text-xs font-semibold text-muted-foreground">
          Focal point — click image or use sliders
        </p>
        <div
          role="button"
          tabIndex={0}
          aria-label="Set image focal point"
          className="relative aspect-[16/11] max-w-md cursor-crosshair overflow-hidden rounded-[var(--radius-md)] border border-border bg-muted"
          onClick={(e) => setFocal(e.clientX, e.clientY, e.currentTarget)}
          onKeyDown={(e) => {
            if (e.key !== "Enter" && e.key !== " ") return;
            e.preventDefault();
            const rect = e.currentTarget.getBoundingClientRect();
            setFocal(rect.left + rect.width / 2, rect.top + rect.height / 2, e.currentTarget);
          }}
        >
          {activeUrl ? (
            <Media
              src={activeUrl}
              alt=""
              className="absolute inset-0 h-full w-full object-cover"
              style={{ objectPosition: `${pct(fx)} ${pct(fy)}` }}
            />
          ) : null}
          <span
            aria-hidden
            className="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-paper bg-accent shadow"
            style={{ left: pct(fx), top: pct(fy) }}
          />
        </div>
        <div className="grid max-w-md gap-2 sm:grid-cols-2">
          <label className="text-xs">
            Horizontal
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round((fx ?? 0.5) * 100)}
              disabled={busy || disabled}
              className="mt-1 w-full"
              onChange={(e) => {
                const x = Number(e.target.value) / 100;
                onChange(
                  role === "hero"
                    ? { ...value, hero_image_focal_x: x }
                    : { ...value, primary_image_focal_x: x },
                );
              }}
            />
          </label>
          <label className="text-xs">
            Vertical
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round((fy ?? 0.5) * 100)}
              disabled={busy || disabled}
              className="mt-1 w-full"
              onChange={(e) => {
                const y = Number(e.target.value) / 100;
                onChange(
                  role === "hero"
                    ? { ...value, hero_image_focal_y: y }
                    : { ...value, primary_image_focal_y: y },
                );
              }}
            />
          </label>
        </div>
      </div>
    </section>
  );
}

export const IMAGE_CAPABLE_LOCATION_KINDS = new Set(["city", "state", "area"]);
