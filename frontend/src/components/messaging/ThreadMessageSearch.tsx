"use client";

import { useId } from "react";

import { cn } from "@/lib/cn";
import { formatMessageSentAt } from "@/lib/format-message-time";
import type { MessageItem } from "@/lib/types/messaging";

export type ThreadSearchFilter = "all" | "starred" | "pinned" | "attachments";

const FILTERS: { value: ThreadSearchFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "starred", label: "Starred" },
  { value: "pinned", label: "Pinned" },
  { value: "attachments", label: "Files" },
];

function resultPreview(message: MessageItem): string {
  const body = (message.body || "").trim();
  if (body) return body.length > 90 ? `${body.slice(0, 87)}…` : body;
  if (message.attachments?.length) {
    return message.attachments[0]?.original_filename || "Attachment";
  }
  return "Message";
}

export function ThreadMessageSearch({
  query,
  filter,
  results,
  loading,
  onQueryChange,
  onFilterChange,
  onSelect,
  onClear,
  className,
}: {
  query: string;
  filter: ThreadSearchFilter;
  results: MessageItem[];
  loading?: boolean;
  onQueryChange: (q: string) => void;
  onFilterChange: (f: ThreadSearchFilter) => void;
  onSelect: (messageId: string) => void;
  onClear: () => void;
  className?: string;
}) {
  const inputId = useId();
  const active = Boolean(query.trim()) || filter !== "all";

  return (
    <div className={cn("space-y-2 border-b border-border px-4 py-2", className)}>
      <div className="flex items-center gap-2">
        <label htmlFor={inputId} className="sr-only">
          Search in conversation
        </label>
        <input
          id={inputId}
          type="search"
          value={query}
          placeholder="Search in conversation…"
          className={cn(
            "min-w-0 flex-1 rounded-[var(--radius-md)] border border-border bg-background",
            "px-3 py-1.5 text-sm text-foreground outline-none",
            "focus-visible:ring-2 focus-visible:ring-focus-ring",
          )}
          onChange={(e) => onQueryChange(e.target.value)}
        />
        {active ? (
          <button
            type="button"
            className="shrink-0 text-xs font-bold text-muted-foreground underline-offset-2 hover:underline"
            onClick={onClear}
          >
            Clear
          </button>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className={cn(
              "rounded-[var(--radius-sm)] px-2 py-1 text-[11px] font-bold",
              filter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-surface-muted text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onFilterChange(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>
      {active ? (
        <div className="max-h-40 overflow-y-auto rounded-[var(--radius-md)] border border-border/70 bg-surface-muted/40">
          {loading ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">Searching…</p>
          ) : results.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              No matching messages
            </p>
          ) : (
            <ul className="divide-y divide-border/60">
              {results.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    className="block w-full px-3 py-2 text-left hover:bg-surface-muted"
                    onClick={() => onSelect(m.id)}
                  >
                    <p className="truncate text-xs font-semibold text-foreground">
                      {resultPreview(m)}
                    </p>
                    <p className="mt-0.5 text-[10px] font-semibold text-muted-foreground">
                      {m.sender_display_name}
                      {m.created_at
                        ? ` · ${formatMessageSentAt(m.created_at)}`
                        : ""}
                      {m.is_starred ? " · Starred" : ""}
                      {m.is_pinned ? " · Pinned" : ""}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
