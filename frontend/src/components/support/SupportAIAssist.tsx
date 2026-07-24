"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { Alert, Button } from "@/components/ui";
import {
  generateSupportTicketAI,
  recordAdminAIGenerationFeedback,
} from "@/lib/ai-api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  FALLBACK_SUPPORT_CATEGORIES,
  formatSupportLabel,
} from "@/lib/support-ui";
import type { AISuggestion } from "@/lib/types/ai";

const FEATURE_SUMMARY = "support.ticket.summary";
const FEATURE_TRIAGE = "support.ticket.triage";
const FEATURE_PRIORITY = "support.ticket.priority";
const FEATURE_REPLY = "support.ticket.reply_draft";
const FEATURE_ARTICLES = "support.ticket.article_suggestions";

const UNAVAILABLE =
  "AI is unavailable right now. You can keep editing manually.";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const detail = err.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return UNAVAILABLE;
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    /* ignore */
  }
}

type PanelKey =
  | "summary"
  | "category"
  | "priority"
  | "reply"
  | "articles"
  | null;

export function SupportAIAssist({
  ticketId,
  canDraftReply = true,
  canApplyTriage = true,
  onApplyReply,
  onApplyCategory,
  onApplyPriority,
  onTicketUpdated,
}: {
  ticketId: string;
  canDraftReply?: boolean;
  canApplyTriage?: boolean;
  onApplyReply?: (draft: string) => void;
  onApplyCategory?: (slug: string) => Promise<void> | void;
  onApplyPriority?: (priority: string) => Promise<void> | void;
  onTicketUpdated?: () => Promise<void> | void;
}) {
  const [busy, setBusy] = useState<PanelKey>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<PanelKey>(null);
  const [result, setResult] = useState<AISuggestion | null>(null);

  const run = useCallback(
    async (feature: string, panel: Exclude<PanelKey, null>) => {
      setBusy(panel);
      setError(null);
      setActive(panel);
      try {
        const data = await generateSupportTicketAI(ticketId, { feature });
        setResult(data);
      } catch (err) {
        setResult(null);
        setError(errorMessage(err));
      } finally {
        setBusy(null);
      }
    },
    [ticketId],
  );

  const feedback = useCallback(
    async (
      action: "applied" | "dismissed",
      appliedField?: string,
      selected?: string,
    ) => {
      if (!result?.usage_log_id) return;
      try {
        await recordAdminAIGenerationFeedback({
          usage_log_id: result.usage_log_id,
          action,
          support_ticket_id: ticketId,
          applied_field: appliedField,
          selected_option: selected,
        });
      } catch {
        /* non-blocking */
      }
    },
    [result?.usage_log_id, ticketId],
  );

  const dismiss = useCallback(async () => {
    await feedback("dismissed");
    setResult(null);
    setActive(null);
    setError(null);
  }, [feedback]);

  const categoryLabel = (slug: string | null | undefined) => {
    if (!slug) return "";
    const hit = FALLBACK_SUPPORT_CATEGORIES.find((c) => c.value === slug);
    return hit?.label ?? formatSupportLabel(slug);
  };

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">AI Assist</p>
        <p className="text-xs text-muted-foreground">
          AI suggestions are drafts. Review before applying or sending.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_SUMMARY, "summary")}
        >
          {busy === "summary" ? "Summarizing…" : "Summarize ticket"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_TRIAGE, "category")}
        >
          {busy === "category" ? "Suggesting…" : "Suggest category"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_PRIORITY, "priority")}
        >
          {busy === "priority" ? "Suggesting…" : "Suggest priority"}
        </Button>
        {canDraftReply ? (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy !== null}
            onClick={() => void run(FEATURE_REPLY, "reply")}
          >
            {busy === "reply" ? "Drafting…" : "Draft reply with AI"}
          </Button>
        ) : null}
        <Button
          size="sm"
          variant="secondary"
          disabled={busy !== null}
          onClick={() => void run(FEATURE_ARTICLES, "articles")}
        >
          {busy === "articles" ? "Searching…" : "Suggest help articles"}
        </Button>
      </div>

      {error ? (
        <Alert tone="danger" title="AI assist">
          {error}
        </Alert>
      ) : null}

      {result && active ? (
        <div
          className={cn(
            "space-y-3 rounded-[var(--radius-md)] border border-border",
            "bg-surface-inset px-4 py-3",
          )}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {result.label}
          </p>

          {active === "articles" && result.articles?.length ? (
            <ul className="space-y-2 text-sm">
              {result.articles.map((a) => (
                <li key={a.id || a.slug || a.title}>
                  {a.path ? (
                    <Link
                      href={a.path}
                      className="font-medium text-primary-text hover:underline"
                    >
                      {a.title || a.slug}
                    </Link>
                  ) : (
                    <span className="font-medium text-foreground">
                      {a.title || a.slug}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm text-foreground">
              {result.suggestion}
            </pre>
          )}

          {active === "priority" && result.priority_reason ? (
            <p className="text-xs text-muted-foreground">
              Reason: {result.priority_reason}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2">
            {active === "summary" || active === "articles" ? (
              <>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void copyText(result.suggestion)}
                >
                  Copy
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy !== null}
                  onClick={() =>
                    void run(
                      active === "summary" ? FEATURE_SUMMARY : FEATURE_ARTICLES,
                      active,
                    )
                  }
                >
                  Regenerate
                </Button>
                <Button size="sm" variant="ghost" onClick={() => void dismiss()}>
                  Dismiss
                </Button>
              </>
            ) : null}

            {active === "category" && result.category_slug ? (
              <>
                {canApplyTriage && onApplyCategory ? (
                  <Button
                    size="sm"
                    disabled={busy !== null}
                    onClick={() =>
                      void (async () => {
                        try {
                          await onApplyCategory(result.category_slug!);
                          await feedback(
                            "applied",
                            "category",
                            result.category_slug || undefined,
                          );
                          setResult(null);
                          setActive(null);
                          await onTicketUpdated?.();
                        } catch {
                          /* keep draft visible */
                        }
                      })()
                    }
                  >
                    Apply suggestion ({categoryLabel(result.category_slug)})
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy !== null}
                  onClick={() => void run(FEATURE_TRIAGE, "category")}
                >
                  Regenerate
                </Button>
                <Button size="sm" variant="ghost" onClick={() => void dismiss()}>
                  Ignore
                </Button>
              </>
            ) : null}

            {active === "priority" && result.priority ? (
              <>
                {canApplyTriage && onApplyPriority ? (
                  <Button
                    size="sm"
                    disabled={busy !== null}
                    onClick={() =>
                      void (async () => {
                        try {
                          await onApplyPriority(result.priority!);
                          await feedback(
                            "applied",
                            "priority",
                            result.priority || undefined,
                          );
                          setResult(null);
                          setActive(null);
                          await onTicketUpdated?.();
                        } catch {
                          /* keep draft visible */
                        }
                      })()
                    }
                  >
                    Apply suggestion ({formatSupportLabel(result.priority)})
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy !== null}
                  onClick={() => void run(FEATURE_PRIORITY, "priority")}
                >
                  Regenerate
                </Button>
                <Button size="sm" variant="ghost" onClick={() => void dismiss()}>
                  Ignore
                </Button>
              </>
            ) : null}

            {active === "reply" ? (
              <>
                {onApplyReply ? (
                  <Button
                    size="sm"
                    onClick={() =>
                      void (async () => {
                        onApplyReply(result.suggestion);
                        await feedback("applied", "reply_body", result.suggestion);
                        setResult(null);
                        setActive(null);
                      })()
                    }
                  >
                    Apply to reply box
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void copyText(result.suggestion)}
                >
                  Copy
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy !== null}
                  onClick={() => void run(FEATURE_REPLY, "reply")}
                >
                  Regenerate
                </Button>
                <Button size="sm" variant="ghost" onClick={() => void dismiss()}>
                  Dismiss
                </Button>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
