import type {
  RuntimeSettingItem,
  RuntimeSettingSource,
  RuntimeSettingStatus,
  RuntimeSettingsCategorySummary,
} from "./runtime-settings-api";

export type SourceBadgeTone = "accent" | "neutral" | "outline" | "warning" | "danger" | "success";

export type DerivedSettingStatus = {
  status: RuntimeSettingStatus;
  label: string;
  tone: SourceBadgeTone;
};

/** Never display raw secrets — only first4…last4 fingerprint when configured. */
export function formatSecretDisplay(opts: {
  configured?: boolean | null;
  masked_value?: string | null;
  first_four?: string | null;
  last_four?: string | null;
}): string {
  const configured = Boolean(opts.configured);
  if (!configured) return "Not configured";

  if (opts.masked_value?.trim()) {
    return opts.masked_value.trim();
  }

  const first = sanitizeFirst(opts.first_four);
  const last =
    sanitizeLast(opts.last_four) || sanitizeLast(extractLastFour(opts.masked_value));
  if (first && last) return `Configured · ${first}…${last}`;
  if (last) return `Configured · ····${last}`;
  if (first) return `Configured · ${first}…`;
  return "Configured";
}

function extractLastFour(masked: string | null | undefined): string | null {
  if (!masked) return null;
  const fingerprint = masked.match(/([A-Za-z0-9]{2,8})…([A-Za-z0-9]{2,8})/);
  if (fingerprint) return sanitizeLast(fingerprint[2]);
  const ending = masked.match(/ending in\s*([A-Za-z0-9]{2,8})\s*$/i);
  if (ending) return sanitizeLast(ending[1]);
  if (/^[A-Za-z0-9]{2,8}$/.test(masked.trim())) {
    return sanitizeLast(masked.trim());
  }
  const alnum = masked.replace(/[^A-Za-z0-9]/g, "");
  if (alnum.length >= 2) return sanitizeLast(alnum);
  return null;
}

function sanitizeFirst(value: string | null | undefined): string | null {
  if (!value) return null;
  const cleaned = value.replace(/[^A-Za-z0-9]/g, "");
  if (cleaned.length < 2) return null;
  return cleaned.slice(0, 4);
}

function sanitizeLast(value: string | null | undefined): string | null {
  if (!value) return null;
  const cleaned = value.replace(/[^A-Za-z0-9]/g, "");
  if (cleaned.length < 2) return null;
  return cleaned.slice(-4);
}

function sanitizeFragment(value: string | null | undefined): string | null {
  return sanitizeLast(value);
}

export function sourceLabel(source: string | null | undefined): string {
  switch ((source || "").toLowerCase()) {
    case "db":
      return "DB";
    case "env":
      return "ENV";
    case "default":
      return "Default";
    default:
      return source ? source.toUpperCase() : "—";
  }
}

export function sourceTone(source: string | null | undefined): SourceBadgeTone {
  switch ((source || "").toLowerCase()) {
    case "db":
      return "accent";
    case "env":
      return "neutral";
    case "default":
      return "outline";
    default:
      return "neutral";
  }
}

/**
 * Prefer API `status` when present; otherwise derive from source + flags.
 */
export function deriveSettingStatus(
  item: Pick<
    RuntimeSettingItem,
    "status" | "source" | "configured" | "enabled" | "is_secret" | "value"
  >,
): DerivedSettingStatus {
  const api = normalizeStatus(item.status);
  if (api) return statusPresentation(api);

  if (item.enabled === false) {
    return statusPresentation("disabled");
  }

  const configured =
    item.configured ??
    (item.is_secret
      ? false
      : item.value !== null && item.value !== undefined && item.value !== "");

  if (!configured && item.is_secret) {
    return statusPresentation("missing");
  }
  if (!configured) {
    return statusPresentation("needs_configuration");
  }

  const source = (item.source || "").toLowerCase() as RuntimeSettingSource | string;
  if (source === "db") return statusPresentation("db_override");
  if (source === "env") return statusPresentation("env_fallback");
  if (source === "default") return statusPresentation("needs_configuration");
  return statusPresentation("configured");
}

export function deriveCategoryStatus(
  card: Pick<
    RuntimeSettingsCategorySummary,
    "status" | "source" | "configured" | "enabled"
  >,
): DerivedSettingStatus {
  const api = normalizeStatus(card.status);
  if (api) return statusPresentation(api);

  if (card.enabled === false) return statusPresentation("disabled");
  if (card.configured === false) return statusPresentation("needs_configuration");

  const source = (card.source || "").toLowerCase();
  if (source === "db") return statusPresentation("db_override");
  if (source === "env") return statusPresentation("env_fallback");
  if (card.configured === true) return statusPresentation("configured");
  return statusPresentation("needs_configuration");
}

function normalizeStatus(
  status: string | null | undefined,
): RuntimeSettingStatus | null {
  if (!status) return null;
  const s = status.toLowerCase().replace(/[-\s]/g, "_");
  const allowed: RuntimeSettingStatus[] = [
    "missing",
    "disabled",
    "needs_configuration",
    "env_fallback",
    "db_override",
    "configured",
    "ok",
  ];
  return (allowed as string[]).includes(s) ? (s as RuntimeSettingStatus) : null;
}

function statusPresentation(status: RuntimeSettingStatus): DerivedSettingStatus {
  switch (status) {
    case "missing":
      return { status, label: "Missing", tone: "danger" };
    case "disabled":
      return { status, label: "Disabled", tone: "neutral" };
    case "needs_configuration":
      return { status, label: "Needs configuration", tone: "warning" };
    case "env_fallback":
      return { status, label: "Using env fallback", tone: "neutral" };
    case "db_override":
      return { status, label: "Using DB override", tone: "accent" };
    case "ok":
    case "configured":
      return { status: "configured", label: "Configured", tone: "success" };
    default:
      return { status: "needs_configuration", label: "Needs configuration", tone: "warning" };
  }
}

/** Categories that use specialist UIs — never a second SMTP/VAPID editor. */
export const SPECIALIST_CATEGORIES: Record<
  string,
  { href: string; label: string }
> = {
  email: { href: "/admin/email/settings", label: "Email settings" },
  push: { href: "/admin/push/settings", label: "Push settings" },
  // Not a runtime-settings registry category — AI feature toggles live here.
  "feature-toggles": { href: "/admin/ai/features", label: "AI feature toggles" },
  features: { href: "/admin/ai/features", label: "AI feature toggles" },
};

export function isSpecialistCategory(category: string): boolean {
  return category in SPECIALIST_CATEGORIES;
}

export function specialistHrefFor(category: string): string | null {
  return SPECIALIST_CATEGORIES[category]?.href ?? null;
}

export function categoryPath(category: string): string {
  return `/admin/settings/runtime/${encodeURIComponent(category)}`;
}

export function formatCategoryLabel(category: string, label?: string | null): string {
  if (label) return label;
  const map: Record<string, string> = {
    email: "Email",
    push: "Push",
    ai: "AI",
    payments: "Payments",
    storage: "Storage",
    integrations: "Integrations",
    features: "Feature toggles",
    "feature-toggles": "Feature toggles",
    notifications: "Notifications",
    "system-status": "System status",
    "security-runtime": "Security runtime",
  };
  return map[category] || category.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Strip anything that looks like a secret from toast/error copy. */
export function sanitizePublicMessage(message: string | null | undefined): string {
  if (!message) return "Something went wrong";
  // Drop long hex/base64-looking blobs and obvious key material.
  return message
    .replace(/\b(?:sk_|pk_|whsec_|Bearer\s+)[A-Za-z0-9\-_=+/]{8,}\b/gi, "[redacted]")
    .replace(/\b[A-Za-z0-9+/_-]{40,}\b/g, "[redacted]")
    .slice(0, 280);
}
