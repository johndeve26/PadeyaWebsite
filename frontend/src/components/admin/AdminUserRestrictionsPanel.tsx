"use client";

import { useMemo, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  ConfirmAction,
  EmptyState,
  Input,
  SectionHeader,
  Select,
  Textarea,
} from "@/components/ui";
import {
  ACCOUNT_RESTRICTION_GROUPS,
  ACCOUNT_STATUS_LABELS,
  FULL_SUSPENSION_RESTRICTIONS,
  RESTRICTION_DURATION_OPTIONS,
  RESTRICTION_PRESETS,
  deriveDisplayAccountStatus,
  endsAtFromDuration,
  formatAdminActor,
  mergeRestrictionPreset,
  restrictionCategoryLabel,
  restrictionLabel,
  type AccountRestriction,
  type RestrictionDurationId,
  type RestrictionPresetId,
} from "@/lib/account-status";
import { formatDateTime } from "@/lib/format";
import type {
  AdminUserDetail,
  AdminUserRestriction,
} from "@/lib/types/lifecycle";

function rowStatusTone(
  status: string,
): "success" | "warning" | "danger" | "neutral" {
  const key = status.toLowerCase();
  if (key === "active") return "warning";
  return "neutral";
}

export function AdminUserRestrictionsPanel({
  detail,
  rows,
  canViewRestrictions,
  canAddRestriction = false,
  canRevokeRestriction = false,
  canSuspend = false,
  canBan = false,
  busy = false,
  onApply,
  onRevoke,
  onExtend,
  onConvertToFullSuspension,
  onUnsuspend,
  onBan,
}: {
  detail: AdminUserDetail;
  rows: AdminUserRestriction[];
  canViewRestrictions: boolean;
  canAddRestriction?: boolean;
  canRevokeRestriction?: boolean;
  canSuspend?: boolean;
  canBan?: boolean;
  busy?: boolean;
  onApply: (payload: {
    restriction_keys: string[];
    reason: string;
    internal_note?: string | null;
    ends_at?: string | null;
  }) => Promise<void> | void;
  onRevoke: (restrictionId: string, reason: string) => Promise<void> | void;
  onExtend: (
    restrictionId: string,
    payload: { ends_at: string; reason?: string },
  ) => Promise<void> | void;
  onConvertToFullSuspension: (payload: {
    restriction_keys: string[];
    reason: string;
    internal_note?: string | null;
    ends_at?: string | null;
  }) => Promise<void> | void;
  onUnsuspend: (reason: string) => Promise<void> | void;
  onBan?: (reason: string) => Promise<void> | void;
}) {
  const activeRows = useMemo(
    () => rows.filter((row) => row.status === "active"),
    [rows],
  );
  const inactiveRows = useMemo(
    () =>
      rows
        .filter((row) => row.status !== "active")
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [rows],
  );

  const displayStatus = deriveDisplayAccountStatus({
    accountStatus: detail.account_status,
    isActive: detail.is_active,
    underReview: detail.under_review || detail.moderation.under_review,
    activeRestrictionCount: activeRows.length,
  });

  const [draft, setDraft] = useState<AccountRestriction[]>([]);
  const [presetId, setPresetId] = useState<"" | RestrictionPresetId>("");
  const [reason, setReason] = useState("");
  const [internalNote, setInternalNote] = useState("");
  const [duration, setDuration] = useState<RestrictionDurationId>("indefinite");
  const [customEndsAt, setCustomEndsAt] = useState("");
  const [confirmedSignature, setConfirmedSignature] = useState("");
  const [extendEndsAt, setExtendEndsAt] = useState<Record<string, string>>({});

  const formSignature = `${draft.join(",")}|${reason}|${duration}|${customEndsAt}`;
  const confirmed = confirmedSignature === formSignature && draft.length > 0;

  const reasonOk = reason.trim().length >= 3;
  const endsAt = endsAtFromDuration(
    duration,
    duration === "custom" ? customEndsAt : undefined,
  );
  const durationOk =
    duration !== "custom" ||
    (Boolean(customEndsAt.trim()) && endsAt != null);
  const canApply =
    canAddRestriction &&
    draft.length > 0 &&
    reasonOk &&
    durationOk &&
    confirmed &&
    !busy;

  function toggleCode(code: AccountRestriction, checked: boolean) {
    setDraft((prev) => {
      const set = new Set(prev);
      if (checked) set.add(code);
      else set.delete(code);
      return ACCOUNT_RESTRICTION_GROUPS.flatMap((g) => [...g.codes]).filter(
        (c) => set.has(c),
      ) as AccountRestriction[];
    });
  }

  function onPresetChange(next: "" | RestrictionPresetId) {
    setPresetId(next);
    if (!next) return;
    const preset = RESTRICTION_PRESETS.find((p) => p.id === next);
    if (!preset) return;
    setDraft((prev) => mergeRestrictionPreset(prev, preset.codes));
  }

  function resetAddForm() {
    setDraft([]);
    setPresetId("");
    setReason("");
    setInternalNote("");
    setDuration("indefinite");
    setCustomEndsAt("");
    setConfirmedSignature("");
  }

  async function handleApply() {
    if (!canApply) return;
    await onApply({
      restriction_keys: draft,
      reason: reason.trim(),
      ...(internalNote.trim() ? { internal_note: internalNote.trim() } : {}),
      ...(endsAt ? { ends_at: endsAt } : { ends_at: null }),
    });
    resetAddForm();
  }

  async function handleFullSuspension() {
    if (!canAddRestriction || !canSuspend || !reasonOk || !confirmed) return;
    const keys = mergeRestrictionPreset(draft, FULL_SUSPENSION_RESTRICTIONS);
    await onConvertToFullSuspension({
      restriction_keys: keys,
      reason: reason.trim(),
      ...(internalNote.trim() ? { internal_note: internalNote.trim() } : {}),
      ...(endsAt ? { ends_at: endsAt } : { ends_at: null }),
    });
    resetAddForm();
  }

  const sortedActive = useMemo(
    () =>
      [...activeRows].sort((a, b) =>
        a.restriction_key.localeCompare(b.restriction_key),
      ),
    [activeRows],
  );

  if (!canViewRestrictions) {
    return (
      <Alert tone="warning" title="Permission required">
        You need <code className="text-xs">admin.users.view_restrictions</code>{" "}
        to view this tab.
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <SectionHeader
          eyebrow="Restrictions"
          title="Selective activity limits"
          description="Choose what this user cannot do. Prefer Messaging, Buyer, Host, or Ambassador presets — not full account block — unless login must be stopped."
        />
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            tone={
              displayStatus === "suspended" || displayStatus === "banned"
                ? "danger"
                : displayStatus === "restricted" ||
                    displayStatus === "under_review"
                  ? "warning"
                  : "success"
            }
            size="sm"
          >
            {ACCOUNT_STATUS_LABELS[displayStatus]}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {activeRows.length} active restriction
            {activeRows.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {canSuspend &&
          (detail.account_status === "suspended" ||
            displayStatus === "suspended") ? (
            <ConfirmAction
              label="Unsuspend / restore account"
              title="Restore account to active?"
              description="Clears suspended status and restores login. Active restriction rows are unchanged."
              confirmLabel="Restore"
              busy={busy}
              requireReason
              reasonLabel="Reason"
              onConfirm={(r) => {
                if (!r?.trim()) return;
                void onUnsuspend(r);
              }}
            />
          ) : null}
          {canBan &&
          detail.account_status !== "banned" &&
          onBan ? (
            <ConfirmAction
              label="Ban account"
              title="Ban this account?"
              description="Stronger permanent block. Prefer selective restrictions or emergency suspend when possible."
              confirmLabel="Ban"
              tone="danger"
              variant="secondary"
              busy={busy}
              requireReason
              reasonLabel="Reason"
              onConfirm={(r) => {
                if (!r?.trim()) return;
                void onBan(r);
              }}
            />
          ) : null}
        </div>
      </Card>

      <Card className="space-y-4">
        <SectionHeader
          eyebrow="Current"
          title="Current restrictions"
          description="Active rows from user_restrictions. Revoke keeps history."
        />
        {sortedActive.length === 0 ? (
          <EmptyState
            title="No active restrictions"
            description="Apply restrictions below to limit specific activities."
          />
        ) : (
          <ul className="space-y-3">
            {sortedActive.map((row) => (
              <li
                key={row.id}
                className="rounded-[var(--radius-md)] border border-border bg-card px-3 py-3 dark:bg-surface-elevated"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 space-y-1 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-foreground">
                        {restrictionLabel(row.restriction_key)}
                      </span>
                      <Badge tone="neutral" size="sm">
                        {restrictionCategoryLabel(row.restriction_key)}
                      </Badge>
                      <Badge tone={rowStatusTone(row.status)} size="sm">
                        {row.status}
                      </Badge>
                    </div>
                    <p className="text-foreground">
                      <span className="text-muted-foreground">Reason: </span>
                      {row.reason}
                    </p>
                    <p className="text-muted-foreground">
                      Starts {formatDateTime(row.starts_at)}
                      {" · "}
                      Ends{" "}
                      {row.ends_at ? formatDateTime(row.ends_at) : "Indefinite"}
                      {" · "}
                      Created by {formatAdminActor(row)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {canAddRestriction ? (
                      <ConfirmAction
                        label="Extend"
                        title="Extend this restriction?"
                        description="Sets a new ends_at. Leave reason blank if not needed."
                        confirmLabel="Extend"
                        size="sm"
                        variant="secondary"
                        busy={busy}
                        disabled={busy || !extendEndsAt[row.id]?.trim()}
                        onConfirm={async () => {
                          const local = extendEndsAt[row.id]?.trim();
                          if (!local) return;
                          const parsed = new Date(local);
                          if (Number.isNaN(parsed.getTime())) return;
                          const note =
                            extendEndsAt[`${row.id}__reason`]?.trim();
                          await onExtend(row.id, {
                            ends_at: parsed.toISOString(),
                            ...(note ? { reason: note } : {}),
                          });
                        }}
                      >
                        <Input
                          label="New ends at"
                          type="datetime-local"
                          value={extendEndsAt[row.id] || ""}
                          onChange={(e) =>
                            setExtendEndsAt((prev) => ({
                              ...prev,
                              [row.id]: e.target.value,
                            }))
                          }
                        />
                        <Textarea
                          label="Reason (optional)"
                          placeholder="Why extending…"
                          rows={2}
                          value={extendEndsAt[`${row.id}__reason`] || ""}
                          onChange={(e) =>
                            setExtendEndsAt((prev) => ({
                              ...prev,
                              [`${row.id}__reason`]: e.target.value,
                            }))
                          }
                        />
                      </ConfirmAction>
                    ) : null}
                    {canRevokeRestriction ? (
                      <ConfirmAction
                        label="Revoke"
                        title="Revoke this restriction?"
                        description="Marks the row revoked (history kept). Reason required."
                        confirmLabel="Revoke"
                        size="sm"
                        tone="danger"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason"
                        onConfirm={(r) => {
                          if (!r?.trim()) return;
                          void onRevoke(row.id, r);
                        }}
                      />
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {canAddRestriction ? (
        <Card className="space-y-4">
          <SectionHeader
            eyebrow="Add"
            title="Choose what to restrict"
            description="Selective first — pick a preset or toggle individual activities. Full account block is emergency-only and lives at the bottom."
          />

          <div className="space-y-2">
            <p className="text-sm font-semibold text-foreground">
              Selective presets
            </p>
            <p className="text-xs text-muted-foreground">
              Applying a preset merges its keys onto the draft (does not clear
              other toggles).
            </p>
            <div className="flex flex-wrap gap-2">
              {RESTRICTION_PRESETS.filter((p) => !p.alsoSuspend).map(
                (preset) => (
                  <Button
                    key={preset.id}
                    type="button"
                    size="sm"
                    variant={presetId === preset.id ? "primary" : "secondary"}
                    disabled={busy}
                    title={preset.description}
                    onClick={() => onPresetChange(preset.id)}
                  >
                    {preset.label}
                  </Button>
                ),
              )}
              {draft.length > 0 ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  onClick={resetAddForm}
                >
                  Clear draft
                </Button>
              ) : null}
            </div>
            {presetId && presetId !== "full_suspension" ? (
              <p className="text-xs text-muted-foreground">
                {
                  RESTRICTION_PRESETS.find((p) => p.id === presetId)
                    ?.description
                }
              </p>
            ) : null}
          </div>

          <div className="space-y-5">
            <p className="text-sm font-semibold text-foreground">
              Individual activities
            </p>
            {ACCOUNT_RESTRICTION_GROUPS.map((group) => (
              <div key={group.id} className="space-y-2">
                <p className="text-sm font-semibold text-foreground">
                  {group.label}
                </p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {group.codes.map((code) => (
                    <Checkbox
                      key={code}
                      id={`add-restriction-${code}`}
                      name={code}
                      label={restrictionLabel(code)}
                      checked={draft.includes(code)}
                      disabled={busy}
                      onChange={(e) => toggleCode(code, e.target.checked)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Textarea
              label="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why these restrictions are being applied…"
              hint="Required (≥3 characters)."
              rows={3}
            />
            <div className="space-y-3">
              <Textarea
                label="Internal note (optional)"
                value={internalNote}
                onChange={(e) => setInternalNote(e.target.value)}
                placeholder="Admin-only context…"
                rows={2}
              />
              <Select
                label="Duration"
                value={duration}
                onChange={(e) =>
                  setDuration(e.target.value as RestrictionDurationId)
                }
              >
                {RESTRICTION_DURATION_OPTIONS.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </Select>
              {duration === "custom" ? (
                <Input
                  label="Custom end date"
                  type="datetime-local"
                  value={customEndsAt}
                  onChange={(e) => setCustomEndsAt(e.target.value)}
                />
              ) : null}
            </div>
          </div>

          <Checkbox
            id="confirm-apply-restrictions"
            label="I confirm these restrictions should be applied to this account."
            checked={confirmed}
            disabled={busy}
            onChange={(e) =>
              setConfirmedSignature(e.target.checked ? formSignature : "")
            }
          />

          <div className="flex flex-wrap gap-2">
            <ConfirmAction
              label="Apply restrictions"
              title="Apply selected restrictions?"
              description={`Creates ${draft.length || 0} restriction row${draft.length === 1 ? "" : "s"} (temporary or indefinite). User can still log in unless separately suspended.`}
              confirmLabel="Apply"
              busy={busy}
              disabled={!canApply}
              onConfirm={() => void handleApply()}
            />
          </div>
          {!reasonOk || !confirmed || draft.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Select keys, enter a reason (≥3 chars), and check the confirmation
              box to enable Apply.
            </p>
          ) : null}

          {canSuspend ? (
            <div className="space-y-3 border-t border-border pt-4">
              <p className="text-sm font-semibold text-foreground">
                Emergency only
              </p>
              <p className="text-xs text-muted-foreground">
                Full account block applies all major activity keys and suspends
                login. Prefer selective restrictions above whenever possible.
              </p>
              <ConfirmAction
                label="Emergency: full account block"
                title="Emergency full account block?"
                description="Last resort — applies all major cannot_* + read_only_account keys, then suspends login. Not the default moderation path."
                confirmLabel="Block & suspend"
                tone="danger"
                variant="secondary"
                busy={busy}
                disabled={
                  !canAddRestriction ||
                  !canSuspend ||
                  !reasonOk ||
                  !confirmed ||
                  !durationOk ||
                  busy
                }
                onConfirm={() => {
                  setPresetId("full_suspension");
                  void handleFullSuspension();
                }}
              />
            </div>
          ) : null}
        </Card>
      ) : (
        <Alert tone="info" title="Cannot add restrictions">
          You need <code className="text-xs">admin.users.add_restriction</code>{" "}
          to apply new restriction keys.
        </Alert>
      )}

      {inactiveRows.length > 0 ? (
        <Card className="space-y-3">
          <SectionHeader
            eyebrow="History"
            title="Revoked & expired"
            description="Soft lifecycle only — rows are never hard-deleted."
          />
          <ul className="space-y-2">
            {inactiveRows.map((row) => (
              <li
                key={row.id}
                className="rounded-[var(--radius-md)] border border-border px-3 py-2 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-foreground">
                    {restrictionLabel(row.restriction_key)}
                  </span>
                  <Badge tone={rowStatusTone(row.status)} size="sm">
                    {row.status}
                  </Badge>
                  <Badge tone="neutral" size="sm">
                    {restrictionCategoryLabel(row.restriction_key)}
                  </Badge>
                </div>
                <p className="mt-1 text-muted-foreground">
                  {row.reason}
                  {" · "}
                  {formatDateTime(row.created_at)}
                  {row.revoked_at
                    ? ` · Revoked ${formatDateTime(row.revoked_at)}`
                    : ""}
                </p>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
