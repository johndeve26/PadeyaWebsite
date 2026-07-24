"use client";

import { useCallback, useState } from "react";

import { Alert, Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  generateHostAI,
  recordHostAIGenerationFeedback,
} from "@/lib/ai-api";
import { cn } from "@/lib/cn";
import {
  MERCH_CATEGORIES,
  MERCH_CATEGORY_LABELS,
  type MerchCategoryValue,
} from "@/lib/merch-product-types";
import type { AISuggestion } from "@/lib/types/ai";

import type { MerchProductFormValues } from "./form/types";

const FEATURE_TITLE = "host.merch.title";
const FEATURE_DESCRIPTION = "host.merch.description";
const FEATURE_CATEGORY = "host.merch.category";
const FEATURE_TAGS = "host.merch.tags";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep editing manually.";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

function fulfillmentLabel(values: MerchProductFormValues): string {
  if (values.pickup_enabled && values.shipping_enabled) return "pickup and shipping";
  if (values.shipping_enabled) return "shipping";
  if (values.pickup_enabled) return "pickup";
  return "unspecified";
}

function inferMerchKind(values: MerchProductFormValues, hasEvent: boolean): string {
  if (values.is_vault_exclusive) return "vault_exclusive";
  if (values.storefront_visibility === "post_event_drop") return "post_event_drop";
  if (hasEvent) return "event_merch";
  return "standalone";
}

function limitedStockFlag(values: MerchProductFormValues): string {
  const low = values.variants.some((v) => {
    const n = Number(v.inventory);
    return Number.isFinite(n) && n > 0 && n <= 10;
  });
  return low ? "yes" : "no";
}

export function merchStudioExtra(
  values: MerchProductFormValues,
  opts: {
    eventTitle?: string | null;
    eventCity?: string | null;
    eventCategory?: string | null;
    eventDate?: string | null;
    hasEvent?: boolean;
    audienceLabel?: string | null;
  },
): Record<string, string> {
  const kind = inferMerchKind(values, Boolean(opts.hasEvent));
  return {
    title: values.name || "",
    name: values.name || "",
    notes: values.short_description || "",
    description: values.description || "",
    short_description: values.short_description || "",
    product_type: values.product_type || "",
    merch_kind: kind,
    marketplace_kind: kind,
    event_title: opts.eventTitle || "",
    event_city: opts.eventCity || "",
    event_category: opts.eventCategory || "",
    event_date: opts.eventDate || "",
    audience_label: opts.audienceLabel || "",
    fulfillment_label: fulfillmentLabel(values),
    limited_stock: limitedStockFlag(values),
    existing_category: values.category || "",
    existing_tags: (values.tags || []).join(", "),
    catalog_categories: MERCH_CATEGORIES.map(
      (c) => `${c.value} (${c.label})`,
    ).join(", "),
  };
}

function DraftHint() {
  return (
    <p className="text-xs text-muted-foreground">
      Draft only — review before publishing. AI suggestions can be edited before
      saving.
    </p>
  );
}

export function MerchTitleAI({
  values,
  eventId,
  merchProductId,
  eventTitle,
  onApplyTitle,
}: {
  values: MerchProductFormValues;
  eventId?: string | null;
  merchProductId?: string | null;
  eventTitle?: string | null;
  onApplyTitle: (title: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE_TITLE,
        event_id: eventId || undefined,
        merch_product_id: merchProductId || undefined,
        notes: values.short_description || undefined,
        extra: merchStudioExtra(values, {
          eventTitle,
          hasEvent: Boolean(eventId),
        }),
      });
      setResult(suggestion);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [eventId, eventTitle, merchProductId, values]);

  const options =
    result?.options && result.options.length > 0
      ? result.options
      : result?.suggestion
        ? result.suggestion
            .split("\n")
            .map((line) => line.replace(/^\d+[.)]\s*/, "").trim())
            .filter((line) => line.length >= 3)
        : [];

  async function applyOption(option: string) {
    onApplyTitle(option);
    if (result?.usage_log_id) {
      void recordHostAIGenerationFeedback({
        usage_log_id: result.usage_log_id,
        action: "applied",
        event_id: eventId || undefined,
        merch_product_id: merchProductId || undefined,
        applied_field: "name",
        selected_option: option,
      }).catch(() => undefined);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void generate()}
        >
          {busy ? "Generating…" : "Generate title ideas"}
        </Button>
        <span className="text-xs text-muted-foreground">Generate with AI</span>
      </div>
      <DraftHint />
      {error ? (
        <Alert tone="warning" title="AI unavailable">
          {error}
        </Alert>
      ) : null}
      {result && options.length > 0 ? (
        <div
          className={cn(
            "space-y-2 rounded-[var(--radius-md)] border border-border/80",
            "bg-muted/30 p-3",
          )}
        >
          <p className="text-xs font-semibold text-muted-foreground">
            Title ideas
            {result.used_fallback ? " · template draft" : ""}
          </p>
          <ul className="space-y-1.5">
            {options.map((opt) => (
              <li key={opt}>
                <button
                  type="button"
                  className={cn(
                    "w-full rounded-[var(--radius-sm)] border border-border/70",
                    "bg-card px-3 py-2 text-left text-sm text-foreground",
                    "hover:border-primary/40 hover:bg-surface-muted",
                  )}
                  onClick={() => void applyOption(opt)}
                >
                  {opt}
                </button>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => void generate()}
            >
              Regenerate
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setResult(null);
                if (result.usage_log_id) {
                  void recordHostAIGenerationFeedback({
                    usage_log_id: result.usage_log_id,
                    action: "dismissed",
                    event_id: eventId || undefined,
                    merch_product_id: merchProductId || undefined,
                  }).catch(() => undefined);
                }
              }}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function MerchDescriptionAI({
  values,
  eventId,
  merchProductId,
  eventTitle,
  onApplyDescription,
}: {
  values: MerchProductFormValues;
  eventId?: string | null;
  merchProductId?: string | null;
  eventTitle?: string | null;
  onApplyDescription: (description: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const generate = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE_DESCRIPTION,
        event_id: eventId || undefined,
        merch_product_id: merchProductId || undefined,
        notes: values.short_description || undefined,
        extra: merchStudioExtra(values, {
          eventTitle,
          hasEvent: Boolean(eventId),
        }),
      });
      setResult(suggestion);
    } catch (err) {
      setResult(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, [eventId, eventTitle, merchProductId, values]);

  async function apply() {
    if (!result?.suggestion) return;
    onApplyDescription(result.suggestion);
    void recordHostAIGenerationFeedback({
      usage_log_id: result.usage_log_id,
      action: "applied",
      event_id: eventId || undefined,
      merch_product_id: merchProductId || undefined,
      applied_field: "description",
    }).catch(() => undefined);
  }

  async function copyText() {
    if (!result?.suggestion || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(result.suggestion);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void generate()}
        >
          {busy ? "Generating…" : "Generate description"}
        </Button>
        <span className="text-xs text-muted-foreground">Generate with AI</span>
      </div>
      <DraftHint />
      {error ? (
        <Alert tone="warning" title="AI unavailable">
          {error}
        </Alert>
      ) : null}
      {result?.suggestion ? (
        <div
          className={cn(
            "space-y-3 rounded-[var(--radius-md)] border border-border/80",
            "bg-muted/30 p-3",
          )}
        >
          <p className="text-xs font-semibold text-muted-foreground">
            Description draft
            {result.used_fallback ? " · template draft" : ""}
          </p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
            {result.suggestion}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" onClick={() => void apply()}>
              Apply
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={busy}
              onClick={() => void generate()}
            >
              Regenerate
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => void copyText()}
            >
              Copy
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setResult(null);
                void recordHostAIGenerationFeedback({
                  usage_log_id: result.usage_log_id,
                  action: "dismissed",
                  event_id: eventId || undefined,
                  merch_product_id: merchProductId || undefined,
                }).catch(() => undefined);
              }}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function MerchCategoryTagAI({
  values,
  eventId,
  merchProductId,
  eventTitle,
  onApplyCategory,
  onApplyTags,
}: {
  values: MerchProductFormValues;
  eventId?: string | null;
  merchProductId?: string | null;
  eventTitle?: string | null;
  onApplyCategory: (slug: string) => void;
  onApplyTags: (tags: string[]) => void;
}) {
  const [busyCat, setBusyCat] = useState(false);
  const [busyTags, setBusyTags] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [catResult, setCatResult] = useState<AISuggestion | null>(null);
  const [tagResult, setTagResult] = useState<AISuggestion | null>(null);

  const generateCategory = useCallback(async () => {
    setBusyCat(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE_CATEGORY,
        event_id: eventId || undefined,
        merch_product_id: merchProductId || undefined,
        notes: values.short_description || undefined,
        extra: merchStudioExtra(values, {
          eventTitle,
          hasEvent: Boolean(eventId),
        }),
      });
      setCatResult(suggestion);
    } catch (err) {
      setCatResult(null);
      setError(errorMessage(err));
    } finally {
      setBusyCat(false);
    }
  }, [eventId, eventTitle, merchProductId, values]);

  const generateTags = useCallback(async () => {
    setBusyTags(true);
    setError(null);
    try {
      const suggestion = await generateHostAI({
        feature: FEATURE_TAGS,
        event_id: eventId || undefined,
        merch_product_id: merchProductId || undefined,
        notes: values.short_description || undefined,
        extra: merchStudioExtra(values, {
          eventTitle,
          hasEvent: Boolean(eventId),
        }),
      });
      setTagResult(suggestion);
    } catch (err) {
      setTagResult(null);
      setError(errorMessage(err));
    } finally {
      setBusyTags(false);
    }
  }, [eventId, eventTitle, merchProductId, values]);

  const suggestedSlug =
    catResult?.category_slug ||
    (catResult?.suggestion
      ? MERCH_CATEGORIES.find(
          (c) =>
            c.value === catResult.suggestion.toLowerCase().trim() ||
            c.label.toLowerCase() === catResult.suggestion.toLowerCase().trim(),
        )?.value
      : undefined);

  const tagOptions =
    tagResult?.tags && tagResult.tags.length > 0
      ? tagResult.tags
      : tagResult?.options && tagResult.options.length > 0
        ? tagResult.options
        : [];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busyCat}
          onClick={() => void generateCategory()}
        >
          {busyCat ? "Suggesting…" : "Suggest category"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busyTags}
          onClick={() => void generateTags()}
        >
          {busyTags ? "Suggesting…" : "Suggest tags"}
        </Button>
        <span className="text-xs text-muted-foreground">Generate with AI</span>
      </div>
      <DraftHint />
      <p className="text-xs text-muted-foreground">
        Categories stay in the controlled Pàdéyá catalog. AI can suggest a
        catalog slug/label only — it cannot invent new browse categories.
      </p>
      {error ? (
        <Alert tone="warning" title="AI unavailable">
          {error}
        </Alert>
      ) : null}
      {catResult && suggestedSlug ? (
        <div
          className={cn(
            "space-y-2 rounded-[var(--radius-md)] border border-border/80",
            "bg-muted/30 p-3",
          )}
        >
          <p className="text-xs font-semibold text-muted-foreground">
            Category suggestion
            {catResult.used_fallback ? " · template draft" : ""}
          </p>
          <p className="text-sm text-foreground">
            {MERCH_CATEGORY_LABELS[suggestedSlug as MerchCategoryValue] ||
              suggestedSlug}{" "}
            <span className="text-muted-foreground">({suggestedSlug})</span>
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => {
                onApplyCategory(suggestedSlug);
                void recordHostAIGenerationFeedback({
                  usage_log_id: catResult.usage_log_id,
                  action: "applied",
                  event_id: eventId || undefined,
                  merch_product_id: merchProductId || undefined,
                  applied_field: "category",
                  selected_option: suggestedSlug,
                }).catch(() => undefined);
              }}
            >
              Apply category
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setCatResult(null)}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
      {tagResult && tagOptions.length > 0 ? (
        <div
          className={cn(
            "space-y-2 rounded-[var(--radius-md)] border border-border/80",
            "bg-muted/30 p-3",
          )}
        >
          <p className="text-xs font-semibold text-muted-foreground">
            Tag suggestions
            {tagResult.used_fallback ? " · template draft" : ""}
          </p>
          <p className="text-sm text-foreground">{tagOptions.join(" · ")}</p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => {
                onApplyTags(tagOptions);
                void recordHostAIGenerationFeedback({
                  usage_log_id: tagResult.usage_log_id,
                  action: "applied",
                  event_id: eventId || undefined,
                  merch_product_id: merchProductId || undefined,
                  applied_field: "tags",
                }).catch(() => undefined);
              }}
            >
              Apply tags
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setTagResult(null)}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
