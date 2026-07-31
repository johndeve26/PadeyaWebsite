"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AdminUserDetailSections } from "@/components/admin/AdminUserDetailSections";
import { AdminUserRestrictionsPanel } from "@/components/admin/AdminUserRestrictionsPanel";
import { ImpersonationHistoryPanel } from "@/components/admin/ImpersonationHistoryPanel";
import { ImpersonationStartModal } from "@/components/admin/ImpersonationStartModal";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  Select,
  SkeletonLoader,
  Textarea,
  useToast,
} from "@/components/ui";
import {
  addAdminUserFlag,
  addAdminUserNote,
  applyAdminUserRestrictions,
  banUser,
  clearAdminUserUnderReview,
  dismissAdminUserFlag,
  extendAdminUserRestriction,
  fetchAdminUser,
  fetchAdminUserRestrictions,
  forceAdminUserPasswordReset,
  forceDeleteUser,
  markAdminUserUnderReview,
  resolveAdminUserFlag,
  revokeAdminUserRestriction,
  revokeAdminUserSessions,
  suspendUser,
  unsuspendUser,
} from "@/lib/admin-lifecycle-api";
import { ApiError, fetchImpersonationHistory } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import type { ImpersonationHistoryItem } from "@/lib/auth/types";
import type {
  AdminUserDetail,
  AdminUserRestriction,
  UserPublic,
} from "@/lib/types/lifecycle";
import {
  ACCOUNT_STATUS_LABELS,
  ACCOUNT_STATUS_TRANSITIONS,
  type AccountStatus,
} from "@/lib/account-status";
import {
  USER_FLAG_SEVERITIES,
  USER_FLAG_TYPE_LABELS,
  USER_FLAG_TYPES,
  type UserFlagSeverity,
  type UserFlagType,
} from "@/lib/user-flags";
import {
  USER_NOTE_TYPE_LABELS,
  USER_NOTE_TYPES,
  type UserNoteType,
} from "@/lib/user-notes";

export default function AdminUserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = String(params.userId ?? "");
  const toast = useToast();
  const { user: adminUser } = useAuth();
  const [detail, setDetail] = useState<AdminUserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiDenied, setApiDenied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [history, setHistory] = useState<ImpersonationHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [noteType, setNoteType] = useState<UserNoteType>("general");
  const [noteBody, setNoteBody] = useState("");
  const [flagType, setFlagType] = useState<UserFlagType>("manual_watchlist");
  const [flagSeverity, setFlagSeverity] =
    useState<UserFlagSeverity>("medium");
  const [flagReason, setFlagReason] = useState("");
  const [flagInternalNote, setFlagInternalNote] = useState("");
  const [restrictionRows, setRestrictionRows] = useState<
    AdminUserRestriction[]
  >([]);

  const canView = userHasPermission(adminUser, "admin.users.view");
  const canViewActivity = userHasPermission(
    adminUser,
    "admin.users.view_activity",
  );
  const canViewSecurity = userHasPermission(
    adminUser,
    "admin.users.view_security",
  );
  const canViewAudit = userHasPermission(adminUser, "admin.users.view_audit");
  const canViewRestrictions = userHasPermission(
    adminUser,
    "admin.users.view_restrictions",
  );
  const canAddRestriction = userHasPermission(
    adminUser,
    "admin.users.add_restriction",
  );
  const canRevokeRestriction = userHasPermission(
    adminUser,
    "admin.users.revoke_restriction",
  );
  const canAddNote = userHasPermission(adminUser, "admin.users.add_note");
  const canFlag = userHasPermission(adminUser, "admin.users.flag");
  const canRestrict = userHasPermission(adminUser, "admin.users.restrict");
  const canSuspend = userHasPermission(adminUser, "admin.users.suspend");
  const canBan = userHasPermission(adminUser, "admin.users.ban");
  const canForceDelete = userHasPermission(adminUser, "admin.users.force_delete");
  const canForceLogout = userHasPermission(adminUser, "admin.users.force_logout");
  const canForcePasswordReset = userHasPermission(
    adminUser,
    "admin.users.force_password_reset",
  );
  const canImpersonate = userHasPermission(adminUser, "admin.users.impersonate");
  const denied = !canView || apiDenied;

  const loadDetail = useCallback(async () => {
    const row = await fetchAdminUser(userId);
    setDetail(row);
    setError(null);
    setApiDenied(false);
    if (canViewRestrictions) {
      try {
        const rows = await fetchAdminUserRestrictions(userId);
        setRestrictionRows(rows);
      } catch {
        setRestrictionRows(
          row.user_restrictions ??
            row.moderation.user_restrictions ??
            [],
        );
      }
    } else {
      setRestrictionRows([]);
    }
  }, [userId, canViewRestrictions]);

  const loadHistory = useCallback(async () => {
    if (!canImpersonate || !userId) return;
    setHistoryLoading(true);
    try {
      const rows = await fetchImpersonationHistory(userId, { limit: 50 });
      setHistory(rows);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [canImpersonate, userId]);

  useEffect(() => {
    if (!canView) return;
    let active = true;
    void (async () => {
      setLoading(true);
      try {
        await loadDetail();
      } catch (err) {
        if (!active) return;
        setDetail(null);
        if (err instanceof ApiError && err.status === 403) {
          setApiDenied(true);
          setError(null);
        } else {
          setApiDenied(false);
          setError(
            err instanceof ApiError ? err.detail : "Could not load this user",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [canView, loadDetail]);

  useEffect(() => {
    if (!canImpersonate || !userId || !canView) return;
    let alive = true;
    void fetchImpersonationHistory(userId, { limit: 50 })
      .then((rows) => {
        if (alive) setHistory(rows);
      })
      .catch(() => {
        if (alive) setHistory([]);
      })
      .finally(() => {
        if (alive) setHistoryLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [canImpersonate, canView, userId]);

  async function runAction(
    title: string,
    action: () => Promise<unknown>,
    successTitle: string,
  ) {
    setBusy(true);
    try {
      await action();
      await loadDetail();
      toast.push({ tone: "success", title: successTitle });
    } catch (err) {
      toast.push({
        tone: "danger",
        title,
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusy(false);
    }
  }

  const openFlags =
    detail?.moderation.admin_flags.filter((f) => f.status === "active") ?? [];

  const impersonationTarget: UserPublic | null = detail
    ? {
        id: detail.id,
        email: detail.email || detail.email_masked,
        full_name: detail.full_name,
        is_active: detail.is_active,
        is_verified: detail.is_verified,
        roles: detail.roles,
        permissions: [],
        created_at: detail.created_at,
        deactivated_at: detail.deactivated_at,
        security_locked: detail.security_locked,
        security_lock_reason: detail.security_lock_reason,
        ambassadors_blocked: detail.ambassadors_blocked,
      }
    : null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title={detail?.display_name || detail?.full_name || "User"}
      description={
        detail
          ? `${detail.email} · Safe Pàdéyá account view — passwords and tokens are never shown.`
          : "Account detail and support actions."
      }
    >
      <div className="mb-4">
        <Link
          href="/admin/users"
          className="text-sm font-semibold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          ← All users
        </Link>
      </div>

      {denied ? (
        <Alert tone="danger" title="Permission denied">
          You need <code className="text-xs">admin.users.view</code> to open
          user management. Ask a super admin if you need access.
        </Alert>
      ) : loading ? (
        <SkeletonLoader lines={8} />
      ) : error ? (
        <Alert tone="danger" title="User not found">
          {error}
        </Alert>
      ) : detail ? (
        <div className="space-y-6">
          <AdminUserDetailSections
            detail={detail}
            canViewActivity={canViewActivity}
            canViewSecurity={canViewSecurity}
            canViewAudit={canViewAudit}
            canViewRestrictions={canViewRestrictions}
            slots={{
              overviewActions: (
                <>
                  {canImpersonate ? (
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => setModalOpen(true)}
                    >
                      Impersonate user
                    </Button>
                  ) : null}
                </>
              ),
              restrictionsPanel: (
                <AdminUserRestrictionsPanel
                  detail={detail}
                  rows={restrictionRows}
                  canViewRestrictions={canViewRestrictions}
                  canAddRestriction={canAddRestriction}
                  canRevokeRestriction={canRevokeRestriction}
                  canSuspend={canSuspend}
                  canBan={canBan}
                  busy={busy}
                  onApply={(payload) =>
                    runAction(
                      "Could not apply restrictions",
                      () => applyAdminUserRestrictions(userId, payload),
                      "Restrictions applied",
                    )
                  }
                  onRevoke={(restrictionId, reason) =>
                    runAction(
                      "Could not revoke restriction",
                      () =>
                        revokeAdminUserRestriction(
                          userId,
                          restrictionId,
                          reason,
                        ),
                      "Restriction revoked",
                    )
                  }
                  onExtend={(restrictionId, payload) =>
                    runAction(
                      "Could not extend restriction",
                      () =>
                        extendAdminUserRestriction(
                          userId,
                          restrictionId,
                          payload,
                        ),
                      "Restriction extended",
                    )
                  }
                  onConvertToFullSuspension={(payload) =>
                    runAction(
                      "Full account block failed",
                      async () => {
                        await applyAdminUserRestrictions(userId, payload);
                        await suspendUser(userId, payload.reason);
                      },
                      "Account blocked and suspended",
                    )
                  }
                  onUnsuspend={(reason) =>
                    runAction(
                      "Unsuspend failed",
                      () => unsuspendUser(userId, reason),
                      "Account restored",
                    )
                  }
                  onBan={(reason) =>
                    runAction(
                      "Ban failed",
                      () => banUser(userId, reason),
                      "Account banned",
                    )
                  }
                />
              ),
              notesActions: canAddNote ? (
                <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/30 p-3">
                  <Select
                    label="Note type"
                    value={noteType}
                    onChange={(e) =>
                      setNoteType(e.target.value as UserNoteType)
                    }
                  >
                    {USER_NOTE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {USER_NOTE_TYPE_LABELS[type]}
                      </option>
                    ))}
                  </Select>
                  <Textarea
                    label="Internal note"
                    value={noteBody}
                    onChange={(e) => setNoteBody(e.target.value)}
                    placeholder="Admin-only context. Never paste passwords, tokens, or payment/QR secrets."
                    hint="Visible only to admins. Never shown to the user."
                    rows={3}
                  />
                  <Button
                    type="button"
                    size="sm"
                    disabled={busy || noteBody.trim().length < 3}
                    onClick={() =>
                      void runAction(
                        "Could not add note",
                        async () => {
                          await addAdminUserNote(userId, {
                            note_type: noteType,
                            body: noteBody,
                          });
                          setNoteBody("");
                          setNoteType("general");
                        },
                        "Note added",
                      )
                    }
                  >
                    Add note
                  </Button>
                </div>
              ) : (
                <Alert tone="info" title="Read only">
                  You can view notes but cannot add them without{" "}
                  <code className="text-xs">admin.users.add_note</code>.
                </Alert>
              ),
              flagsActions: (
                <div className="space-y-4">
                  {canFlag ? (
                    <div className="space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/30 p-3">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <Select
                          label="Flag type"
                          value={flagType}
                          onChange={(e) =>
                            setFlagType(e.target.value as UserFlagType)
                          }
                        >
                          {USER_FLAG_TYPES.map((type) => (
                            <option key={type} value={type}>
                              {USER_FLAG_TYPE_LABELS[type]}
                            </option>
                          ))}
                        </Select>
                        <Select
                          label="Severity"
                          value={flagSeverity}
                          onChange={(e) =>
                            setFlagSeverity(e.target.value as UserFlagSeverity)
                          }
                        >
                          {USER_FLAG_SEVERITIES.map((severity) => (
                            <option key={severity} value={severity}>
                              {severity.charAt(0).toUpperCase() +
                                severity.slice(1)}
                            </option>
                          ))}
                        </Select>
                      </div>
                      <Textarea
                        label="Reason"
                        value={flagReason}
                        onChange={(e) => setFlagReason(e.target.value)}
                        placeholder="Why this flag is being added…"
                        rows={2}
                      />
                      <Textarea
                        label="Internal note (optional)"
                        value={flagInternalNote}
                        onChange={(e) => setFlagInternalNote(e.target.value)}
                        placeholder="Extra context for other admins…"
                        rows={2}
                      />
                      <Button
                        type="button"
                        size="sm"
                        disabled={busy || flagReason.trim().length < 3}
                        onClick={() =>
                          void runAction(
                            "Could not add flag",
                            async () => {
                              await addAdminUserFlag(userId, {
                                flag_type: flagType,
                                severity: flagSeverity,
                                reason: flagReason,
                                internal_note: flagInternalNote || undefined,
                              });
                              setFlagReason("");
                              setFlagInternalNote("");
                              setFlagSeverity("medium");
                            },
                            "Flag added",
                          )
                        }
                      >
                        Add flag
                      </Button>
                    </div>
                  ) : (
                    <Alert tone="info" title="Read only">
                      You can view flags but cannot create or close them without{" "}
                      <code className="text-xs">admin.users.flag</code>.
                    </Alert>
                  )}

                  {canFlag && openFlags.length > 0 ? (
                    <div className="space-y-3">
                      <p className="text-sm font-semibold text-foreground">
                        Close active flags
                      </p>
                      <ul className="space-y-2">
                        {openFlags.map((flag) => (
                          <li
                            key={flag.id}
                            className="flex flex-col gap-2 rounded-[var(--radius-md)] border border-border px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
                          >
                            <div className="min-w-0 text-sm">
                              <p className="font-semibold text-foreground">
                                {USER_FLAG_TYPE_LABELS[
                                  flag.flag_type as UserFlagType
                                ] || flag.flag_type}{" "}
                                · {flag.severity}
                              </p>
                              <p className="text-muted-foreground">
                                {flag.reason}
                              </p>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              <ConfirmAction
                                label="Resolve"
                                title="Resolve this flag?"
                                description="Marks the flag as resolved. Reason is required and audited."
                                confirmLabel="Resolve"
                                size="sm"
                                busy={busy}
                                requireReason
                                reasonLabel="Reason"
                                onConfirm={(reason) => {
                                  if (!reason?.trim()) return;
                                  void runAction(
                                    "Resolve failed",
                                    () =>
                                      resolveAdminUserFlag(
                                        userId,
                                        flag.id,
                                        reason,
                                      ),
                                    "Flag resolved",
                                  );
                                }}
                              />
                              <ConfirmAction
                                label="Dismiss"
                                title="Dismiss this flag?"
                                description="Dismisses the flag without treating it as confirmed. Reason is required and audited."
                                confirmLabel="Dismiss"
                                size="sm"
                                variant="secondary"
                                busy={busy}
                                requireReason
                                reasonLabel="Reason"
                                onConfirm={(reason) => {
                                  if (!reason?.trim()) return;
                                  void runAction(
                                    "Dismiss failed",
                                    () =>
                                      dismissAdminUserFlag(
                                        userId,
                                        flag.id,
                                        reason,
                                      ),
                                    "Flag dismissed",
                                  );
                                }}
                              />
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ),
              securityActions: (
                <div className="space-y-4 border-t border-border pt-4">
                  <div className="flex flex-wrap gap-2">
                    {canForceLogout ? (
                      <ConfirmAction
                        label="Force logout"
                        title="Revoke all sessions?"
                        description="Invalidates refresh tokens so the user must sign in again. Access JWTs expire naturally."
                        confirmLabel="Force logout"
                        tone="danger"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason"
                        onConfirm={(reason) =>
                          void runAction(
                            "Force logout failed",
                            () =>
                              revokeAdminUserSessions(
                                userId,
                                reason?.trim() || "Force logout",
                              ),
                            "Sessions revoked",
                          )
                        }
                      />
                    ) : null}
                    {canForcePasswordReset ? (
                      <ConfirmAction
                        label="Force password reset email"
                        title="Send password reset email?"
                        description="Emails a one-time reset link. The raw token is never shown in admin UI."
                        confirmLabel="Send email"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason"
                        onConfirm={(reason) =>
                          void runAction(
                            "Password reset failed",
                            () =>
                              forceAdminUserPasswordReset(
                                userId,
                                reason?.trim() || "Force password reset",
                              ),
                            "Reset email sent",
                          )
                        }
                      />
                    ) : null}
                    {canRestrict &&
                    (detail.account_status === "under_review" ||
                      detail.under_review ||
                      detail.moderation.under_review) ? (
                      <ConfirmAction
                        label="Clear under review"
                        title="Return account to active?"
                        description="Clears under-review and sets status to active. Reason required."
                        confirmLabel="Set active"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason"
                        onConfirm={(reason) => {
                          if (!reason?.trim()) return;
                          void runAction(
                            "Clear review failed",
                            () => clearAdminUserUnderReview(userId, reason),
                            "Status set to active",
                          );
                        }}
                      />
                    ) : canRestrict && detail.account_status === "active" ? (
                      <ConfirmAction
                        label="Mark under review"
                        title="Mark account under review?"
                        description="Sets status to under_review without suspending login."
                        confirmLabel="Mark under review"
                        busy={busy}
                        requireReason
                        reasonLabel="Review reason"
                        onConfirm={(reason) => {
                          if (!reason?.trim()) return;
                          void runAction(
                            "Mark review failed",
                            () => markAdminUserUnderReview(userId, reason),
                            "Marked under review",
                          );
                        }}
                      />
                    ) : null}
                    {canSuspend &&
                    (
                      ACCOUNT_STATUS_TRANSITIONS[detail.account_status] || []
                    ).includes("suspended") ? (
                      <ConfirmAction
                        label="Emergency: block login"
                        title="Emergency suspend (block login)?"
                        description="Prefer selective Restrictions when possible. This suspends login and revokes sessions."
                        confirmLabel="Suspend login"
                        tone="danger"
                        variant="secondary"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason for suspension"
                        onConfirm={(reason) => {
                          if (!reason?.trim()) return;
                          void runAction(
                            "Suspend failed",
                            () => suspendUser(userId, reason),
                            "User suspended",
                          );
                        }}
                      />
                    ) : null}
                    {canBan &&
                    detail.account_status !== "banned" &&
                    (
                      ACCOUNT_STATUS_TRANSITIONS[detail.account_status] || []
                    ).includes("banned") ? (
                      <ConfirmAction
                        label="Ban account"
                        title="Ban this account?"
                        description="Stronger permanent block. Prefer selective restrictions when possible."
                        confirmLabel="Ban"
                        tone="danger"
                        variant="secondary"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason"
                        onConfirm={(reason) => {
                          if (!reason?.trim()) return;
                          void runAction(
                            "Ban failed",
                            () => banUser(userId, reason),
                            "User banned",
                          );
                        }}
                      />
                    ) : null}
                    {canSuspend && detail.account_status === "suspended" ? (
                      <ConfirmAction
                        label="Unsuspend / restore"
                        title="Restore account to active?"
                        description="Sets status to active and restores login."
                        confirmLabel="Set active"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason"
                        onConfirm={(reason) => {
                          if (!reason?.trim()) return;
                          void runAction(
                            "Unsuspend failed",
                            () => unsuspendUser(userId, reason),
                            "User unsuspended",
                          );
                        }}
                      />
                    ) : null}
                    {canForceDelete && detail.account_status === "suspended" ? (
                      <ConfirmAction
                        label="Force delete"
                        title="Force-delete this suspended account?"
                        description="Soft end-of-life only — commerce history stays. The account leaves the default user directory. Must already be suspended."
                        confirmLabel="Force delete"
                        tone="danger"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason for force delete"
                        onConfirm={(reason) => {
                          if (!reason?.trim()) return;
                          void (async () => {
                            setBusy(true);
                            try {
                              await forceDeleteUser(userId, reason);
                              toast.push({
                                tone: "success",
                                title: "User force-deleted",
                              });
                              router.push("/admin/users");
                            } catch (err) {
                              toast.push({
                                tone: "danger",
                                title: "Force delete failed",
                                description:
                                  err instanceof ApiError
                                    ? err.detail
                                    : "Try again",
                              });
                            } finally {
                              setBusy(false);
                            }
                          })();
                        }}
                      />
                    ) : null}
                    {canSuspend && detail.account_status === "banned" ? (
                      <ConfirmAction
                        label="Unban / restore"
                        title="Restore banned account to active?"
                        description="Sets status to active and restores login."
                        confirmLabel="Set active"
                        busy={busy}
                        requireReason
                        reasonLabel="Reason"
                        onConfirm={(reason) => {
                          if (!reason?.trim()) return;
                          void runAction(
                            "Unban failed",
                            () => unsuspendUser(userId, reason),
                            "User restored",
                          );
                        }}
                      />
                    ) : null}
                  </div>
                  {!canForceLogout &&
                  !canForcePasswordReset &&
                  !canRestrict &&
                  !canSuspend &&
                  !canBan &&
                  !canForceDelete ? (
                    <Alert tone="info" title="No security actions available">
                      Your role can view security details but cannot force
                      logout, reset password, or change account status.
                    </Alert>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Prefer the Restrictions tab for selective limits. Status:{" "}
                      {ACCOUNT_STATUS_LABELS[
                        detail.account_status as AccountStatus
                      ] || detail.account_status}
                      . Suspend/Ban are emergency global blocks. Force delete
                      requires suspension first (soft EOL).
                    </p>
                  )}
                </div>
              ),
              auditExtra: canImpersonate ? (
                <ImpersonationHistoryPanel
                  className="max-w-4xl"
                  rows={history}
                  loading={historyLoading}
                />
              ) : null,
            }}
          />

          {canImpersonate && impersonationTarget ? (
            <ImpersonationStartModal
              open={modalOpen}
              onClose={() => {
                setModalOpen(false);
                void loadHistory();
              }}
              target={impersonationTarget}
            />
          ) : null}
        </div>
      ) : null}
    </DashboardShell>
  );
}
