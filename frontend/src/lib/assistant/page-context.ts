import type { AssistantPageContext } from "@/lib/types/assistant";

const MAX_ROUTE_KEY = 160;
const MAX_TITLE = 120;
const MAX_ENTITY = 80;
const MAX_TAB = 64;
const MAX_ERRORS = 5;
const MAX_ERROR_LEN = 120;
const MAX_ACTIONS = 12;

function trimOrNull(value: string | null | undefined, max: number): string | null {
  if (!value) return null;
  const cleaned = value.trim().slice(0, max);
  return cleaned || null;
}

/**
 * Build safe page context for the assistant — no tokens, emails, or secrets.
 */
export function buildAssistantPageContext(opts: {
  pathname: string;
  pageTitle?: string | null;
  role?: string | null;
  entityPublicId?: string | null;
  activeTab?: string | null;
  uiErrors?: string[];
  featureFlags?: Record<string, boolean>;
  availableActions?: string[];
}): AssistantPageContext {
  const path = (opts.pathname || "/").split("?")[0] || "/";
  const routeKey = trimOrNull(path, MAX_ROUTE_KEY);

  const entity =
    trimOrNull(opts.entityPublicId, MAX_ENTITY) ??
    inferEntityPublicId(path);

  return {
    route_key: routeKey,
    page_title: trimOrNull(opts.pageTitle, MAX_TITLE),
    role: trimOrNull(opts.role, 32),
    entity_public_id: entity,
    active_tab: trimOrNull(opts.activeTab, MAX_TAB),
    ui_errors: (opts.uiErrors ?? [])
      .map((e) => String(e).trim().slice(0, MAX_ERROR_LEN))
      .filter(Boolean)
      .slice(0, MAX_ERRORS),
    feature_flags: opts.featureFlags ?? {},
    available_actions: (opts.availableActions ?? [])
      .map((a) => String(a).trim().slice(0, 64))
      .filter(Boolean)
      .slice(0, MAX_ACTIONS),
  };
}

/** Best-effort public id from common public routes — never query params. */
function inferEntityPublicId(path: string): string | null {
  const patterns = [
    /^\/events\/([^/]+)/,
    /^\/hosts\/([^/]+)/,
    /^\/legacy\/([^/]+)/,
    /^\/merch\/([^/]+)/,
    /^\/blog\/([^/]+)/,
  ];
  for (const re of patterns) {
    const m = path.match(re);
    if (m?.[1] && m[1] !== "search" && m[1] !== "new") {
      return m[1].slice(0, MAX_ENTITY);
    }
  }
  return null;
}

/**
 * Map auth roles to a single assistant context role (priority order).
 */
export function resolveAssistantRole(
  roles: string[] | null | undefined,
): string | null {
  if (!roles?.length) return null;
  const set = new Set(roles.map((r) => r.toLowerCase()));
  if (set.has("super_admin") || set.has("admin")) return "admin";
  if (set.has("host") || set.has("host_staff")) return "host";
  if (set.has("sponsor")) return "sponsor";
  if (set.has("ambassador")) return "ambassador";
  if (set.has("fan") || set.has("user")) return "fan";
  return roles[0]?.toLowerCase() ?? null;
}
