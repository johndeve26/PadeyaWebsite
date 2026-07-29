import type { APIRequestContext, Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * Demo personas for authenticated UI audit.
 * Passwords MUST come from env (PLAYWRIGHT_PASSWORD or role-specific) — never commit.
 * Local demo seed password is documented in docs/DEMO_DATA.md only.
 */

export type Persona =
  | "fan"
  | "host"
  | "host_staff"
  | "admin_support"
  | "admin_finance"
  | "super_admin";

const DEFAULT_EMAILS: Record<Persona, string> = {
  fan: "fan1@demo.padeye.test",
  host: "host@demo.padeye.test",
  host_staff: "staff@demo.padeye.test",
  admin_support: "support@demo.padeye.test",
  admin_finance: "finance@demo.padeye.test",
  super_admin: "admin@demo.padeye.test",
};

const EMAIL_ENV: Record<Persona, string> = {
  fan: "PLAYWRIGHT_FAN_EMAIL",
  host: "PLAYWRIGHT_HOST_EMAIL",
  host_staff: "PLAYWRIGHT_HOST_STAFF_EMAIL",
  admin_support: "PLAYWRIGHT_ADMIN_SUPPORT_EMAIL",
  admin_finance: "PLAYWRIGHT_ADMIN_FINANCE_EMAIL",
  super_admin: "PLAYWRIGHT_SUPER_ADMIN_EMAIL",
};

export type PersonaCreds = { email: string; password: string };

export function getPersonaCreds(persona: Persona): PersonaCreds | null {
  const email =
    process.env[EMAIL_ENV[persona]]?.trim() || DEFAULT_EMAILS[persona];
  const password =
    process.env[`PLAYWRIGHT_${persona.toUpperCase()}_PASSWORD`]?.trim() ||
    process.env.PLAYWRIGHT_PASSWORD?.trim() ||
    process.env.PLAYWRIGHT_DEMO_PASSWORD?.trim() ||
    "";
  if (!email || !password) return null;
  return { email, password };
}

export function apiBaseUrl(): string {
  return (
    process.env.PLAYWRIGHT_API_URL?.replace(/\/$/, "") ||
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000"
  );
}

export function apiPrefix(): string {
  return process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1";
}

/** Login via API, inject tokens, reload so AuthProvider remounts with session. */
export async function loginAs(
  page: Page,
  request: APIRequestContext,
  persona: Persona,
): Promise<PersonaCreds> {
  const creds = getPersonaCreds(persona);
  if (!creds) {
    throw new Error(
      `Missing credentials for ${persona}. Set PLAYWRIGHT_PASSWORD (and optional role emails).`,
    );
  }

  const url = `${apiBaseUrl()}${apiPrefix()}/auth/login`;
  const res = await request.post(url, {
    data: { login: creds.email, password: creds.password },
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok()) {
    const body = await res.text();
    throw new Error(
      `Login failed for ${persona} (${creds.email}): ${res.status()} ${body.slice(0, 200)}`,
    );
  }
  const tokens = (await res.json()) as {
    access_token: string;
    refresh_token: string;
  };

  // Origin must exist before localStorage write; reload remounts AuthProvider.
  await page.goto("/login", { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.evaluate(
    ({ access, refresh }) => {
      localStorage.setItem("padeya.access_token", access);
      localStorage.setItem("padeya.refresh_token", refresh);
      localStorage.removeItem("padeya.impersonating");
    },
    { access: tokens.access_token, refresh: tokens.refresh_token },
  );
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60_000 });

  // Confirmed session chrome (user menu initials / Create event) or settle.
  await page
    .waitForFunction(
      () => {
        const text = document.body?.innerText || "";
        return /Create event|Personal|Dashboard|Sign out|Log out/i.test(text);
      },
      { timeout: 30_000 },
    )
    .catch(() => undefined);

  return creds;
}

const STATE_DIR = path.join("artifacts", "ui-audit", "auth-state");

export function storageStatePath(persona: Persona): string {
  return path.join(STATE_DIR, `${persona}.json`);
}

/** Persist Playwright storage state (local file only — gitignored). */
export async function saveStorageState(
  page: Page,
  persona: Persona,
): Promise<string> {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const out = storageStatePath(persona);
  await page.context().storageState({ path: out });
  return out;
}

export function hasAuthCredentials(): boolean {
  return Boolean(
    process.env.PLAYWRIGHT_PASSWORD?.trim() ||
      process.env.PLAYWRIGHT_DEMO_PASSWORD?.trim() ||
      process.env.PLAYWRIGHT_FAN_PASSWORD?.trim(),
  );
}
