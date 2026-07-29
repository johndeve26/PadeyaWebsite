/** Client-side blog draft creation helpers — idempotency and template recovery. */

const CREATION_KEY_PREFIX = "padeya-blog-creation:";
const PENDING_TEMPLATE_KEY = "padeya-blog-pending-template";

export type PendingTemplateApplication = {
  postId: string;
  templateSlug: string;
  tab: "write" | "plan";
  creationKey: string;
  createdAt: string;
};

function sessionStore(): Storage | null {
  try {
    if (typeof sessionStorage === "undefined") return null;
    return sessionStorage;
  } catch {
    return null;
  }
}

export function newCreationKey(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `creation-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function readCreationResult(key: string): string | null {
  const store = sessionStore();
  if (!store) return null;
  try {
    return store.getItem(`${CREATION_KEY_PREFIX}${key}`);
  } catch {
    return null;
  }
}

export function writeCreationResult(key: string, postId: string) {
  const store = sessionStore();
  if (!store) return;
  try {
    store.setItem(`${CREATION_KEY_PREFIX}${key}`, postId);
  } catch {
    /* ignore */
  }
}

export function clearCreationResult(key: string) {
  const store = sessionStore();
  if (!store) return;
  try {
    store.removeItem(`${CREATION_KEY_PREFIX}${key}`);
  } catch {
    /* ignore */
  }
}

export function readPendingTemplate(): PendingTemplateApplication | null {
  const store = sessionStore();
  if (!store) return null;
  try {
    const raw = store.getItem(PENDING_TEMPLATE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as PendingTemplateApplication;
  } catch {
    return null;
  }
}

export function writePendingTemplate(pending: PendingTemplateApplication) {
  const store = sessionStore();
  if (!store) return;
  try {
    store.setItem(PENDING_TEMPLATE_KEY, JSON.stringify(pending));
  } catch {
    /* ignore */
  }
}

export function clearPendingTemplate() {
  const store = sessionStore();
  if (!store) return;
  try {
    store.removeItem(PENDING_TEMPLATE_KEY);
  } catch {
    /* ignore */
  }
}
