"use client";

import { useState, type FormEvent } from "react";

import {
  Alert,
  Badge,
  Button,
  Input,
} from "@/components/ui";
import { RuntimeSettingSourceBadge } from "@/components/admin/runtime-settings/RuntimeSettingSourceBadge";
import { formatSecretDisplay } from "@/lib/runtime-settings-display";
import type { RuntimeSettingItem } from "@/lib/runtime-settings-api";

type Props = {
  setting: RuntimeSettingItem;
  canEditSecrets: boolean;
  canClear: boolean;
  busy?: boolean;
  error?: string | null;
  onReplace: (secretValue: string) => Promise<void>;
  onClearOverride: () => Promise<void>;
};

/**
 * Secrets UI: status only ("Configured · ending in 1234" / "Not configured").
 * Replace via password input — never display the current value.
 */
export function SecretSettingField({
  setting,
  canEditSecrets,
  canClear,
  busy = false,
  error = null,
  onReplace,
  onClearOverride,
}: Props) {
  const [replacing, setReplacing] = useState(false);
  const [secretDraft, setSecretDraft] = useState("");

  const display = formatSecretDisplay({
    configured: setting.configured,
    masked_value: setting.masked_value,
    first_four: setting.first_four,
    last_four: setting.last_four,
  });

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canEditSecrets || !setting.editable || busy) return;
    if (!secretDraft.trim()) return;
    await onReplace(secretDraft);
    setSecretDraft("");
    setReplacing(false);
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="space-y-3 rounded-[var(--radius-md)] border border-border bg-card p-4 dark:bg-surface-elevated"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold text-heading">{setting.label}</h3>
            <Badge tone="warning" size="sm">
              Secret
            </Badge>
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

      <Alert tone="warning" title="Secret value">
        Current value is never shown. When configured, only the first and last four
        characters are displayed (for example <span className="font-mono">AIza…jzyk</span>).
      </Alert>

      <p className="text-sm font-semibold text-foreground" data-testid="secret-display">
        {display}
      </p>

      {error || setting.validation_error ? (
        <Alert tone="danger" title="Validation">
          {error || setting.validation_error}
        </Alert>
      ) : null}

      {canEditSecrets && setting.editable ? (
        replacing ? (
          <div className="space-y-3">
            <Input
              id={`secret-${setting.key}`}
              label="Replace secret"
              type="password"
              autoComplete="new-password"
              value={secretDraft}
              onChange={(e) => setSecretDraft(e.target.value)}
              disabled={busy}
              hint="Submit replaces the stored secret. Leave blank and cancel to keep the existing value."
              error={error || undefined}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                size="sm"
                disabled={busy || !secretDraft.trim()}
              >
                {busy ? "Saving…" : "Save secret"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => {
                  setSecretDraft("");
                  setReplacing(false);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={busy}
            onClick={() => setReplacing(true)}
          >
            Replace secret
          </Button>
        )
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
    </form>
  );
}
