"use client";

import { Badge, StatusBadge } from "@/components/ui";
import {
  ACCOUNT_STATUS_LABELS,
  type AccountStatus,
} from "@/lib/account-status";

export function accountStatusToneLabel(status: string | undefined | null): {
  status: string;
  label: string;
} {
  const key = (status || "active").toLowerCase();
  const label =
    ACCOUNT_STATUS_LABELS[key as AccountStatus] ||
    key.replaceAll("_", " ");
  return { status: key, label };
}

export function riskTone(
  level: string | undefined | null,
): "success" | "warning" | "danger" | "neutral" {
  const key = (level || "").toLowerCase();
  if (key === "high") return "danger";
  if (key === "medium") return "warning";
  if (key === "low") return "success";
  return "neutral";
}

export function severityTone(
  severity: string | undefined | null,
): "success" | "warning" | "danger" | "neutral" {
  const key = (severity || "").toLowerCase();
  if (key === "critical" || key === "high") return "danger";
  if (key === "medium") return "warning";
  return "neutral";
}

export function flagStatusTone(
  status: string | undefined | null,
): "success" | "warning" | "danger" | "neutral" {
  const key = (status || "").toLowerCase();
  if (key === "active") return "warning";
  if (key === "resolved") return "success";
  return "neutral";
}

export function AccountStatusBadge({
  status,
}: {
  status: string | undefined | null;
}) {
  const { status: key, label } = accountStatusToneLabel(status);
  return <StatusBadge status={key} label={label} />;
}

export function RiskBadge({
  level,
  label,
}: {
  level: string | undefined | null;
  label?: string | null;
}) {
  const text = label || (level ? `${level} risk` : "Risk");
  return (
    <Badge tone={riskTone(level)} size="sm">
      {text}
    </Badge>
  );
}

export function AdminUserSignalBadges({
  accountStatus,
  isActive,
  isVerified,
  underReview,
  securityLocked,
  ambassadorsBlocked,
  riskLevel,
  riskLabel,
  activeFlagCount,
  restrictionCount,
}: {
  accountStatus?: string | null;
  isActive?: boolean;
  isVerified?: boolean;
  underReview?: boolean;
  securityLocked?: boolean;
  ambassadorsBlocked?: boolean;
  riskLevel?: string | null;
  riskLabel?: string | null;
  activeFlagCount?: number;
  restrictionCount?: number;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <AccountStatusBadge
        status={
          accountStatus ||
          (isActive === false ? "suspended" : "active")
        }
      />
      {riskLevel ? (
        <RiskBadge level={riskLevel} label={riskLabel || undefined} />
      ) : null}
      {underReview &&
      accountStatus !== "under_review" &&
      accountStatus !== "restricted" ? (
        <Badge tone="warning" size="sm">
          Under review
        </Badge>
      ) : null}
      {typeof restrictionCount === "number" &&
      restrictionCount > 0 &&
      accountStatus !== "restricted" ? (
        <Badge tone="warning" size="sm">
          {restrictionCount} restriction
          {restrictionCount === 1 ? "" : "s"}
        </Badge>
      ) : typeof restrictionCount === "number" &&
        restrictionCount > 0 &&
        accountStatus === "restricted" ? (
        <Badge tone="neutral" size="sm">
          {restrictionCount} restriction
          {restrictionCount === 1 ? "" : "s"}
        </Badge>
      ) : null}
      {securityLocked ? (
        <Badge tone="danger" size="sm">
          Locked
        </Badge>
      ) : null}
      {isVerified === false ? (
        <Badge tone="neutral" size="sm">
          Unverified
        </Badge>
      ) : null}
      {ambassadorsBlocked ? (
        <Badge tone="warning" size="sm">
          Ambassadors blocked
        </Badge>
      ) : null}
      {typeof activeFlagCount === "number" && activeFlagCount > 0 ? (
        <Badge tone="warning" size="sm">
          {activeFlagCount} flag{activeFlagCount === 1 ? "" : "s"}
        </Badge>
      ) : null}
    </div>
  );
}
