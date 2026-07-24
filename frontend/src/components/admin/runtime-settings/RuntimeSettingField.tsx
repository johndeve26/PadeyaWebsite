"use client";

import { useState, type FormEvent } from "react";

import {
  Alert,
  Badge,
  Button,
  Input,
  Switch,
} from "@/components/ui";
import { RuntimeSettingSourceBadge } from "@/components/admin/runtime-settings/RuntimeSettingSourceBadge";
import type { RuntimeSettingItem } from "@/lib/runtime-settings-api";

type Props = {
  setting: RuntimeSettingItem;
  canEdit: boolean;
  canClear: boolean;
  busy?: boolean;
  error?: string | null;
  onSave: (value: string | number | boolean | null) => Promise<void>;
  onClearOverride: () => Promise<void>;
  onCancel?: () => void;
};

export function RuntimeSettingField({
  setting,
  canEdit,
  canClear,
  busy = false,
  error = null,
  onSave,
  onClearOverride,
  onCancel,
}: Props) {
  const initial = valueToInput(setting);
  const [draft, setDraft] = useState(initial);
  const [boolDraft, setBoolDraft] = useState(Boolean(setting.value));
  const dirty =
    setting.value_type === "bool"
      ? boolDraft !== Boolean(setting.value)
      : draft !== initial;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canEdit || !setting.editable || busy) return;
    if (setting.value_type === "bool") {
      await onSave(boolDraft);
      return;
    }
    if (setting.value_type === "int" || setting.value_type === "float") {
      const n = Number(draft);
      if (!Number.isFinite(n)) return;
      await onSave(setting.value_type === "int" ? Math.trunc(n) : n);
      return;
    }
    await onSave(draft === "" ? null : draft);
  }

  function handleCancel() {
    setDraft(initial);
    setBoolDraft(Boolean(setting.value));
    onCancel?.();
  }

  const readOnly = !canEdit || !setting.editable;

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="space-y-3 rounded-[var(--radius-md)] border border-border bg-card p-4 dark:bg-surface-elevated"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold text-heading">{setting.label}</h3>
            {setting.restart_required ? (
              <Badge tone="warning" size="sm">
                Restart required
              </Badge>
            ) : null}
          </div>
          {setting.description ? (
            <p className="text-xs leading-relaxed text-muted-foreground">
              {setting.description}
            </p>
          ) : null}
          <p className="font-mono text-[11px] text-muted-foreground">{setting.key}</p>
        </div>
        <RuntimeSettingSourceBadge item={setting} />
      </div>

      {setting.value_type === "bool" ? (
        <Switch
          id={`rs-${setting.key}`}
          checked={boolDraft}
          onCheckedChange={setBoolDraft}
          disabled={readOnly || busy}
          label={setting.label}
          description="Toggle this runtime flag"
        />
      ) : (
        <Input
          id={`rs-${setting.key}`}
          label={
            setting.admin_unit === "mb"
              ? "Value (MB)"
              : setting.validation_schema_json?.unit === "mb"
                ? "Value (MB)"
                : "Value"
          }
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={readOnly || busy}
          type={
            setting.value_type === "int" || setting.value_type === "float"
              ? "number"
              : "text"
          }
          step={
            setting.admin_unit === "mb" ||
            setting.validation_schema_json?.unit === "mb"
              ? "0.1"
              : undefined
          }
          min={
            typeof setting.validation_schema_json?.min === "number"
              ? setting.validation_schema_json.min
              : undefined
          }
          max={
            typeof setting.validation_schema_json?.max === "number"
              ? setting.validation_schema_json.max
              : undefined
          }
          hint={
            setting.admin_unit === "mb"
              ? "Stored as bytes on the server; edit in megabytes."
              : undefined
          }
          error={error || setting.validation_error || undefined}
        />
      )}

      {(error || setting.validation_error) && setting.value_type === "bool" ? (
        <Alert tone="danger" title="Validation">
          {error || setting.validation_error}
        </Alert>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {canEdit && setting.editable ? (
          <>
            <Button type="submit" size="sm" disabled={busy || !dirty}>
              {busy ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={busy || !dirty}
              onClick={handleCancel}
            >
              Cancel
            </Button>
          </>
        ) : null}
        {canClear && setting.source === "db" ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={busy}
            onClick={() => void onClearOverride()}
          >
            Clear DB override
          </Button>
        ) : null}
      </div>
    </form>
  );
}

function valueToInput(setting: RuntimeSettingItem): string {
  if (setting.value === null || setting.value === undefined) return "";
  return String(setting.value);
}
