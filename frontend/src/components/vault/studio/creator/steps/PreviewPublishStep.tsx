"use client";

import { useState } from "react";

import type { VaultItemEditorValues } from "@/components/vault/studio/VaultItemEditor";
import { VaultPreviewPanel } from "@/components/vault/studio/VaultPreviewPanel";
import { Alert, Badge, Button, Card, Input } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatAccessType } from "@/lib/vault-lock-copy";

import {
  buildVaultPublishChecklist,
  valuesToDraftPreviewItem,
} from "../types";

type PreviewTab = "public" | "locked" | "unlock";

type Props = {
  values: VaultItemEditorValues;
  onChange: (next: VaultItemEditorValues) => void;
  previewChecked: boolean;
  onPreviewChecked: (value: boolean) => void;
  scheduleAt: string;
  onScheduleAtChange: (value: string) => void;
};

const TABS: { id: PreviewTab; label: string; hint: string }[] = [
  {
    id: "public",
    label: "Public preview",
    hint: "Catalog / Legacy teaser — no locked body",
  },
  {
    id: "locked",
    label: "Locked preview",
    hint: "What fans see before they unlock",
  },
  {
    id: "unlock",
    label: "Unlock preview",
    hint: "Full content after entitlement",
  },
];

export function PreviewPublishStep({
  values,
  onChange,
  previewChecked,
  onPreviewChecked,
  scheduleAt,
  onScheduleAtChange,
}: Props) {
  const [tab, setTab] = useState<PreviewTab>("locked");
  const checklist = buildVaultPublishChecklist(values, { previewChecked });
  const requiredLeft = checklist.filter((c) => c.required && !c.done);
  const previewItem = valuesToDraftPreviewItem(values, tab);
  const accessLabel = formatAccessType(values.access.access_type);

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-xl font-extrabold text-foreground">
          Preview & Publish
        </h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Confirm what the public, locked, and unlocked experiences look like —
          then save, schedule, or publish.
        </p>
      </div>

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="accent">{values.content_type.replace(/_/g, " ")}</Badge>
          <Badge tone="dark">{accessLabel}</Badge>
          <Badge tone="neutral">{values.status}</Badge>
        </div>
        <p className="text-lg font-extrabold text-foreground">
          {values.title.trim() || "Untitled drop"}
        </p>
        <p className="text-sm text-muted-foreground">
          /@you/vault/{values.slug.trim() || "untitled"}
        </p>
      </Card>

      <div className="flex flex-wrap gap-2">
        {TABS.map((row) => {
          const active = tab === row.id;
          return (
            <button
              key={row.id}
              type="button"
              onClick={() => setTab(row.id)}
              className={cn(
                "rounded-[var(--radius-md)] border px-3 py-2 text-left transition-colors",
                active
                  ? "border-ink bg-ink text-paper"
                  : "border-border bg-surface-inset text-muted-foreground hover:border-border-strong hover:text-foreground",
              )}
            >
              <span className="block text-sm font-extrabold">{row.label}</span>
              <span
                className={cn(
                  "mt-0.5 block text-xs",
                  active ? "text-subtle-foreground" : "text-muted-foreground",
                )}
              >
                {row.hint}
              </span>
            </button>
          );
        })}
      </div>

      <VaultPreviewPanel
        item={previewItem}
        mode={tab === "unlock" ? "owner" : "fan"}
        surfaceLabel={
          tab === "public"
            ? "Public preview · catalog teaser"
            : tab === "locked"
              ? "Locked preview · before unlock"
              : "Unlock preview · after entitlement"
        }
      />

      <label className="flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-muted/50 px-4 py-3 text-sm">
        <input
          type="checkbox"
          className="mt-0.5 accent-accent"
          checked={previewChecked}
          onChange={(e) => onPreviewChecked(e.target.checked)}
        />
        <span>
          <span className="font-semibold text-foreground">
            I reviewed public, locked, and unlock previews
          </span>
          <span className="mt-0.5 block text-muted-foreground">
            Required before publishing. Locked bodies and private media must stay
            protected.
          </span>
        </span>
      </label>

      <Card className="space-y-4">
        <div>
          <h3 className="text-base font-extrabold text-foreground">
            Publish checklist
          </h3>
          <p className="text-sm text-muted-foreground">
            {requiredLeft.length === 0
              ? "Ready to publish or schedule."
              : `${requiredLeft.length} required item${requiredLeft.length === 1 ? "" : "s"} left.`}
          </p>
        </div>
        <ul className="space-y-2">
          {checklist.map((item) => (
            <li
              key={item.id}
              className="flex items-start gap-2 text-sm text-foreground"
            >
              <span
                className={cn(
                  "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-extrabold",
                  item.done
                    ? "bg-[color-mix(in_srgb,var(--brand-green)_35%,transparent)]"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {item.done ? "✓" : "·"}
              </span>
              <span>
                {item.label}
                {!item.required ? (
                  <span className="text-muted-foreground"> · optional</span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="space-y-3">
        <h3 className="text-base font-extrabold text-foreground">Schedule</h3>
        <p className="text-sm text-muted-foreground">
          Schedule publishes the drop and sets the access start window. Fans see
          it as not yet unlockable until that time.
        </p>
        <Input
          label="Go-live / access starts at"
          type="datetime-local"
          value={scheduleAt}
          onChange={(e) => {
            onScheduleAtChange(e.target.value);
            onChange({
              ...values,
              access: { ...values.access, starts_at: e.target.value },
            });
          }}
          hint="Used by the Schedule action. Syncs with access starts at."
        />
      </Card>

      {requiredLeft.length > 0 ? (
        <Alert tone="warning" title="Finish the checklist before publishing">
          {requiredLeft.map((item) => item.label).join(" · ")}
        </Alert>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => setTab("public")}
        >
          Jump to public preview
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => setTab("locked")}
        >
          Jump to locked preview
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => setTab("unlock")}
        >
          Jump to unlock preview
        </Button>
      </div>
    </div>
  );
}
