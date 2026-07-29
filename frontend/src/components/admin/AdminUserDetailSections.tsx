"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import {
  AdminUserSignalBadges,
  flagStatusTone,
  severityTone,
} from "@/components/admin/AdminUserBadges";
import { AdminUserActivityPanel } from "@/components/admin/AdminUserActivityPanel";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  SectionHeader,
  Tabs,
} from "@/components/ui";
import {
  ACCOUNT_STATUS_LABELS,
  activeRestrictionKeysFromDetail,
  deriveDisplayAccountStatus,
  restrictionLabel,
  type AccountStatus,
} from "@/lib/account-status";
import { formatDateTime } from "@/lib/format";
import {
  GENDER_LABELS,
  GENDER_VISIBILITY_LABELS,
  isGender,
  isGenderVisibility,
} from "@/lib/gender";
import type { AdminUserDetail } from "@/lib/types/lifecycle";
import {
  USER_FLAG_TYPE_LABELS,
  type UserFlagType,
} from "@/lib/user-flags";
import {
  USER_NOTE_TYPE_LABELS,
  type UserNoteType,
} from "@/lib/user-notes";

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-foreground">{children}</dd>
    </div>
  );
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export type AdminUserDetailSlots = {
  overviewActions?: ReactNode;
  flagsActions?: ReactNode;
  notesActions?: ReactNode;
  securityActions?: ReactNode;
  restrictionsPanel?: ReactNode;
  auditExtra?: ReactNode;
};

export function AdminUserDetailSections({
  detail,
  slots,
  canViewActivity = true,
  canViewSecurity = true,
  canViewAudit = true,
  canViewRestrictions = false,
}: {
  detail: AdminUserDetail;
  slots?: AdminUserDetailSlots;
  canViewActivity?: boolean;
  canViewSecurity?: boolean;
  canViewAudit?: boolean;
  canViewRestrictions?: boolean;
}) {
  const { profile, account, activity, moderation, recent_audit } = detail;
  const underReview = detail.under_review || moderation.under_review;
  const underReviewReason =
    detail.under_review_reason || moderation.under_review_reason;
  const underReviewAt = detail.under_review_at || moderation.under_review_at;
  const activeFlags = moderation.admin_flags.filter((f) => f.status === "active");
  const notes = moderation.internal_notes;
  const activeRestrictionKeys = activeRestrictionKeysFromDetail(detail);
  const displayStatus = deriveDisplayAccountStatus({
    accountStatus: detail.account_status,
    isActive: detail.is_active,
    underReview,
    activeRestrictionCount: activeRestrictionKeys.length,
  });

  const overview = (
    <div className="space-y-4">
      <Card className="space-y-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-2">
            <SectionHeader
              eyebrow="Overview"
              title={detail.display_name || detail.full_name}
              description={
                detail.username ? `@${detail.username}` : "No username set"
              }
            />
            <AdminUserSignalBadges
              accountStatus={displayStatus}
              isActive={detail.is_active}
              isVerified={detail.is_verified}
              underReview={underReview}
              securityLocked={detail.security_locked}
              ambassadorsBlocked={detail.ambassadors_blocked}
              riskLevel={detail.risk_level}
              riskLabel={`Risk: ${detail.risk_label}`}
              activeFlagCount={activeFlags.length}
              restrictionCount={activeRestrictionKeys.length}
            />
            {underReview && underReviewReason ? (
              <p className="text-sm text-muted-foreground">
                Review reason: {underReviewReason}
                {underReviewAt ? ` · ${formatDateTime(underReviewAt)}` : ""}
              </p>
            ) : null}
          </div>
          {slots?.overviewActions ? (
            <div className="flex flex-wrap gap-2">{slots.overviewActions}</div>
          ) : null}
        </div>

        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Email">{detail.email}</Field>
          <Field label="Created">{formatDateTime(detail.created_at)}</Field>
          <Field label="Last active">
            {formatDateTime(detail.last_active_at)}
          </Field>
          <Field label="User ID">
            <span className="break-all font-mono text-xs">{detail.id}</span>
          </Field>
          <Field label="Roles">{detail.roles.join(", ") || "—"}</Field>
          {detail.deactivated_at ? (
            <Field label="Deactivated">
              {formatDateTime(detail.deactivated_at)}
            </Field>
          ) : null}
        </dl>

        <Alert tone="info" title="Safe account view">
          Passwords, password hashes, session tokens, QR secrets, raw payment
          payloads, and private message bodies are never shown here.
        </Alert>
      </Card>

      <Card className="space-y-4">
        <SectionHeader
          eyebrow="Profile"
          title="Public profile"
          description="Passport and community signals available for this account."
        />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          {profile.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={profile.avatar_url}
              alt=""
              className="h-20 w-20 shrink-0 rounded-[var(--radius-md)] object-cover"
            />
          ) : (
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-[var(--radius-md)] border border-border bg-surface-muted text-sm font-bold text-muted-foreground">
              No photo
            </div>
          )}
          <dl className="grid min-w-0 flex-1 gap-3 text-sm sm:grid-cols-2">
            <Field label="Tagline">{profile.tagline || "—"}</Field>
            <Field label="Passport visibility">
              {profile.passport_visibility
                ? statusLabel(profile.passport_visibility)
                : "No passport"}
              {profile.passport_admin_hidden ? (
                <Badge tone="warning" size="sm" className="ml-2">
                  Hidden
                </Badge>
              ) : null}
            </Field>
            <Field label="Fan Connect">
              {statusLabel(profile.fan_connect_status)}
            </Field>
            <Field label="Gender">
              {profile.gender_unset
                ? "Unset"
                : isGender(profile.gender)
                  ? GENDER_LABELS[profile.gender]
                  : profile.gender_label || profile.gender || "—"}
            </Field>
            <Field label="Gender visibility">
              {isGenderVisibility(profile.gender_visibility)
                ? GENDER_VISIBILITY_LABELS[profile.gender_visibility]
                : profile.gender_visibility || "—"}
            </Field>
            <Field label="Ambassador">
              {profile.ambassadors_program_blocked
                ? "Program blocked"
                : profile.ambassador_profile_status
                  ? statusLabel(profile.ambassador_profile_status)
                  : "No profile"}
              {profile.campaigns_joined > 0
                ? ` · ${profile.campaigns_joined} campaign${profile.campaigns_joined === 1 ? "" : "s"}`
                : ""}
            </Field>
            <div className="sm:col-span-2">
              <Field label="Bio">{profile.bio || "—"}</Field>
            </div>
          </dl>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <Link
            href="/admin/fans"
            className="font-semibold text-foreground underline-offset-2 hover:underline"
          >
            Fan Passports
          </Link>
          <span className="text-muted-foreground">·</span>
          <Link
            href={`/admin/fan-connect/users/${encodeURIComponent(detail.id)}`}
            className="font-semibold text-foreground underline-offset-2 hover:underline"
          >
            Fan Connect moderation
          </Link>
        </div>
      </Card>

      <Card className="space-y-3">
        <SectionHeader
          eyebrow="Moderation summary"
          title="Restrictions & signals"
        />
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <Field label="Derived flags">
            {moderation.flags.length
              ? moderation.flags.map(statusLabel).join(", ")
              : "None"}
          </Field>
          <Field label="Suspensions">
            {moderation.suspensions.length
              ? moderation.suspensions.map(statusLabel).join(", ")
              : "None"}
          </Field>
          <div className="sm:col-span-2">
            <Field label="Restrictions">
              {activeRestrictionKeys.length ? (
                <ul className="mt-1 list-disc space-y-1 pl-5">
                  {activeRestrictionKeys.map((code) => (
                    <li key={code}>{restrictionLabel(code)}</li>
                  ))}
                </ul>
              ) : moderation.restrictions.length ? (
                <ul className="mt-1 list-disc space-y-1 pl-5">
                  {moderation.restrictions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                "None"
              )}
            </Field>
          </div>
          <Field label="Display status">
            {ACCOUNT_STATUS_LABELS[displayStatus as AccountStatus] ||
              displayStatus}
          </Field>
        </dl>
      </Card>
    </div>
  );

  const activityTab = canViewActivity ? (
    <AdminUserActivityPanel userId={detail.id} activity={activity} />
  ) : (
    <Alert tone="warning" title="Permission required">
      You need activity view permission to see this section.
    </Alert>
  );

  const flagsTab = (
    <div className="space-y-4">
      <Card className="space-y-4">
        <SectionHeader
          eyebrow="Flags"
          title="Admin flags"
          description="Watchlists and risk markers. Soft-close only — no hard delete."
        />
        {slots?.flagsActions}
        {moderation.admin_flags.length === 0 ? (
          <EmptyState
            title="No flags"
            description="Add a flag when this account needs ops attention."
          />
        ) : (
          <ul className="space-y-3">
            {moderation.admin_flags.map((flag) => (
              <li
                key={flag.id}
                className="rounded-[var(--radius-md)] border border-border bg-card px-3 py-3 dark:bg-surface-elevated"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-foreground">
                    {USER_FLAG_TYPE_LABELS[flag.flag_type as UserFlagType] ||
                      statusLabel(flag.flag_type)}
                  </span>
                  <Badge tone={severityTone(flag.severity)} size="sm">
                    {statusLabel(flag.severity)}
                  </Badge>
                  <Badge tone={flagStatusTone(flag.status)} size="sm">
                    {statusLabel(flag.status)}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-foreground">{flag.reason}</p>
                {flag.internal_note ? (
                  <p className="mt-1 text-sm text-muted-foreground">
                    Internal: {flag.internal_note}
                  </p>
                ) : null}
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDateTime(flag.created_at)}
                  {flag.resolution_note ? ` · ${flag.resolution_note}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );

  const notesTab = (
    <div className="space-y-4">
      <Card className="space-y-4">
        <SectionHeader
          eyebrow="Notes"
          title="Internal notes"
          description="Admin-only. Never shown to the user."
        />
        {slots?.notesActions}
        {notes.length === 0 ? (
          <EmptyState
            title="No notes yet"
            description="Add context for other admins handling this account."
          />
        ) : (
          <ul className="space-y-3">
            {notes.map((note) => (
              <li
                key={note.id}
                className="rounded-[var(--radius-md)] border border-border bg-surface-muted/40 px-3 py-3"
              >
                <Badge tone="neutral" size="sm">
                  {USER_NOTE_TYPE_LABELS[note.note_type as UserNoteType] ||
                    statusLabel(note.note_type)}
                </Badge>
                <p className="mt-2 whitespace-pre-wrap text-sm text-foreground">
                  {note.body}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDateTime(note.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );

  const securityTab = canViewSecurity ? (
    <div className="space-y-4">
      <Card className="space-y-4">
        <SectionHeader
          eyebrow="Security"
          title="Identity & sessions"
          description="Authentication summary and account controls."
        />
        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Email verified">
            {account.email_verified ? "Yes" : "No"}
          </Field>
          <Field label="Auth provider">{account.auth_provider}</Field>
          <Field label="Roles">{account.roles.join(", ") || "—"}</Field>
          <Field label="Phone">
            {account.phone_available
              ? account.phone_masked || "—"
              : "Not stored"}
          </Field>
          <Field label="2FA">
            {account.two_factor_status === "not_implemented"
              ? "Not available"
              : statusLabel(account.two_factor_status)}
          </Field>
          <Field label="Active sessions">{account.active_sessions}</Field>
          <Field label="Last active">
            {formatDateTime(account.last_active_at)}
          </Field>
          <Field label="Security lock">
            {detail.security_locked
              ? detail.security_lock_reason || "Locked"
              : "Not locked"}
          </Field>
        </dl>
        {slots?.securityActions}
      </Card>
    </div>
  ) : (
    <Alert tone="warning" title="Permission required">
      You need security view permission to see this section.
    </Alert>
  );

  const auditTab = canViewAudit ? (
    <div className="space-y-4">
      <Card className="space-y-4">
        <SectionHeader
          eyebrow="Audit"
          title="Recent admin actions"
          description="Lifecycle and admin actions where this user is the resource."
        />
        {recent_audit.length === 0 ? (
          <EmptyState
            title="No recent admin actions"
            description="Notes, flags, status changes, and session actions will appear here."
          />
        ) : (
          <ul className="divide-y divide-border">
            {recent_audit.map((row) => (
              <li
                key={row.id}
                className="flex flex-col gap-1 py-3 text-sm sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="font-semibold text-foreground">{row.action}</p>
                  <p className="text-muted-foreground">
                    {row.actor_user_id
                      ? `Actor ${row.actor_user_id.slice(0, 8)}…`
                      : "System"}
                    {row.details && "reason" in row.details
                      ? ` · ${String(row.details.reason)}`
                      : ""}
                  </p>
                </div>
                <p className="shrink-0 text-muted-foreground">
                  {formatDateTime(row.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
        <Link
          href={`/admin/audit-logs?resource_type=user&resource_id=${encodeURIComponent(detail.id)}`}
          className="inline-block text-sm font-semibold text-foreground underline-offset-2 hover:underline"
        >
          Open full audit logs
        </Link>
      </Card>
      {slots?.auditExtra}
    </div>
  ) : (
    <Alert tone="warning" title="Permission required">
      You need audit view permission to see this section.
    </Alert>
  );

  const restrictionsTab = canViewRestrictions ? (
    slots?.restrictionsPanel || (
      <Alert tone="info" title="Restrictions">
        Restriction controls load here when available.
      </Alert>
    )
  ) : (
    <Alert tone="warning" title="Permission required">
      You need <code className="text-xs">admin.users.view_restrictions</code> to
      view restrictions.
    </Alert>
  );

  return (
    <Tabs
      defaultId="overview"
      items={[
        { id: "overview", label: "Overview", content: overview },
        { id: "activity", label: "Activity", content: activityTab },
        {
          id: "restrictions",
          label: activeRestrictionKeys.length
            ? `Restrictions (${activeRestrictionKeys.length})`
            : "Restrictions",
          content: restrictionsTab,
        },
        {
          id: "flags",
          label: activeFlags.length
            ? `Flags (${activeFlags.length})`
            : "Flags",
          content: flagsTab,
        },
        {
          id: "notes",
          label: notes.length ? `Notes (${notes.length})` : "Notes",
          content: notesTab,
        },
        { id: "security", label: "Security", content: securityTab },
        { id: "audit", label: "Audit", content: auditTab },
      ]}
    />
  );
}
