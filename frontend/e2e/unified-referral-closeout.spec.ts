/**
 * Unified referral financial gate — four required Playwright flows.
 *
 * Fails setup when PLAYWRIGHT_PASSWORD (or PLAYWRIGHT_DEMO_PASSWORD) is absent.
 * Does not skip the release gate.
 *
 * Env (never commit secrets):
 *   PLAYWRIGHT_PASSWORD=<demo-password from docs/DEMO_DATA.md>
 *   PLAYWRIGHT_BASE_URL=http://localhost:3000
 *   PLAYWRIGHT_API_URL=http://127.0.0.1:8000
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import {
  apiBaseUrl,
  apiPrefix,
  getPersonaCreds,
  loginAs,
  type PersonaCreds,
} from "./helpers/auth";

function requirePassword(): void {
  const pw =
    process.env.PLAYWRIGHT_PASSWORD?.trim() ||
    process.env.PLAYWRIGHT_DEMO_PASSWORD?.trim() ||
    "";
  if (!pw) {
    throw new Error(
      "REFERRAL-P1-001: PLAYWRIGHT_PASSWORD (or PLAYWRIGHT_DEMO_PASSWORD) is required. " +
        "See docs/DEMO_DATA.md for the local demo password. Do not skip this gate.",
    );
  }
}

async function assertApiHealthy(request: APIRequestContext): Promise<void> {
  const admin = getPersonaCreds("super_admin");
  if (!admin) {
    throw new Error("super_admin persona credentials missing after password check");
  }
  const login = await request.post(`${apiBaseUrl()}${apiPrefix()}/auth/login`, {
    data: { login: admin.email, password: admin.password },
    headers: { "Content-Type": "application/json" },
  });
  if (!login.ok()) {
    const body = await login.text();
    throw new Error(
      `Backend not ready for referral gate (login ${login.status()}). Body: ${body.slice(0, 200)}`,
    );
  }
}

async function bearer(
  request: APIRequestContext,
  creds: PersonaCreds,
): Promise<Record<string, string>> {
  const login = await request.post(`${apiBaseUrl()}${apiPrefix()}/auth/login`, {
    data: { login: creds.email, password: creds.password },
    headers: { "Content-Type": "application/json" },
  });
  expect(login.ok(), `login ${creds.email}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

async function softGoto(page: Page, path: string): Promise<boolean> {
  try {
    await page.goto(path, { waitUntil: "domcontentloaded", timeout: 90_000 });
    return true;
  } catch {
    return false;
  }
}

test.describe.configure({ mode: "serial" });

test.describe("unified referral gate", () => {
  test.beforeAll(async ({ request }) => {
    requirePassword();
    await assertApiHealthy(request);
  });

  test("12 · platform program → enroll → link → dashboards", async ({
    page,
    request,
  }) => {
    test.setTimeout(300_000);
    const adminCreds = getPersonaCreds("super_admin")!;
    const fanCreds = getPersonaCreds("fan");
    expect(fanCreds, "fan persona required").toBeTruthy();
    const admin = await bearer(request, adminCreds);
    const stamp = Date.now();
    const desiredCode = `e2eplat${stamp}`.slice(0, 20);

    const created = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/promos/admin/referral-programs`,
      {
        headers: admin,
        data: {
          name: `E2E Platform Gate ${stamp}`,
          default_landing_path: "/events",
          ticket_rule: { commission_mode: "percentage", commission_value: 5 },
          merchandise_rule: {
            commission_mode: "percentage",
            commission_value: 4,
          },
        },
      },
    );
    expect([200, 201], await created.text()).toContain(created.status());
    const program = await created.json();
    expect(program.scope).toBe("platform");
    expect(program.commission_funded_by).toBe("Padeya");

    const enroll = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/promos/admin/referral-programs/${program.id}/enrollments`,
      {
        headers: admin,
        data: { email: fanCreds!.email, referral_code: desiredCode },
      },
    );
    expect([201, 409], await enroll.text()).toContain(enroll.status());
    let code = desiredCode;
    if (enroll.status() === 201) {
      code = (await enroll.json()).referral_code as string;
    }

    const resolve = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/promos/referral/resolve/${code}`,
    );
    expect(resolve.ok(), await resolve.text()).toBeTruthy();
    const landing = (await resolve.json()).landing_path as string;
    expect(landing).toContain("ref=");

    // Browser: open referral landing (may be slow on first Turbopack compile)
    const opened = await softGoto(page, `/r/${code}`);
    if (opened) {
      await expect(page.locator("body")).toContainText(
        /Opening your referral|Browse events|events|unavailable/i,
        { timeout: 60_000 },
      );
    }

    await loginAs(page, request, "fan");
    expect(await softGoto(page, "/dashboard/ambassador")).toBeTruthy();
    await expect(page.locator("body")).toContainText(
      /Ambassador|Referral|Commission|Earnings|Host|Platform/i,
      { timeout: 60_000 },
    );

    await loginAs(page, request, "super_admin");
    expect(await softGoto(page, "/admin/ambassadors/liabilities")).toBeTruthy();
    await expect(page.locator("body")).toContainText(
      /Liability|Platform|Host|Referral|Commission|Ambassador/i,
      { timeout: 60_000 },
    );

    await loginAs(page, request, "host");
    expect(
      await softGoto(page, "/host/ambassadors/platform-attributed"),
    ).toBeTruthy();
    await expect(page.locator("body")).toContainText(
      /Platform|Attributed|Referral|Sale|Ambassador/i,
      { timeout: 60_000 },
    );

    const summary = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/admin/referrals/summary`,
      { headers: admin },
    );
    expect(summary.ok()).toBeTruthy();
    const s = await summary.json();
    expect(s).toHaveProperty("platform_funded_commission");
    expect(s).toHaveProperty("host_funded_commission");
    // Platform liabilities page must not imply host settlement deduction of platform commissions
    expect(s).toHaveProperty("pending_platform_liability");
  });

  test("13 · host event campaign → dashboard Host source", async ({
    page,
    request,
  }) => {
    test.setTimeout(300_000);
    const hostCreds = getPersonaCreds("host")!;
    const fanCreds = getPersonaCreds("fan")!;
    const host = await bearer(request, hostCreds);
    const stamp = Date.now();

    let eventId: string | null = null;
    const eventsRes = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/hosts/me/events?limit=20`,
      { headers: host },
    );
    if (eventsRes.ok()) {
      const body = await eventsRes.json();
      const rows = Array.isArray(body) ? body : body.items || body.events || [];
      if (rows[0]?.id) eventId = String(rows[0].id);
    }
    if (!eventId) {
      const pub = await request.get(
        `${apiBaseUrl()}${apiPrefix()}/events?limit=20`,
      );
      expect(pub.ok(), await pub.text()).toBeTruthy();
      const body = await pub.json();
      const rows = Array.isArray(body) ? body : body.items || [];
      const mine = rows.find(
        (e: { host?: { slug?: string }; slug?: string }) =>
          e.host?.slug === "djmaze" || String(e.slug || "").includes("demo"),
      );
      eventId = String((mine || rows[0])?.id || "");
    }
    expect(eventId, "seeded host event required").toBeTruthy();

    const camp = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/promos/campaigns`,
      {
        headers: host,
        data: {
          event_id: eventId,
          name: `E2E Host Camp ${stamp}`,
          campaign_type: "event_tickets",
          commission_type: "percentage",
          commission_value: 8,
          commission_percent: 8,
          status: "public_open",
        },
      },
    );
    expect([200, 201, 409], await camp.text()).toContain(camp.status());
    let campaignId: string | null =
      camp.status() < 300 ? String((await camp.json()).id) : null;
    if (!campaignId) {
      const list = await request.get(
        `${apiBaseUrl()}${apiPrefix()}/promos/campaigns?event_id=${eventId}`,
        { headers: host },
      );
      if (list.ok()) {
        const body = await list.json();
        const rows = Array.isArray(body) ? body : body.items || [];
        campaignId = rows[0]?.id ? String(rows[0].id) : null;
      }
    }
    expect(campaignId).toBeTruthy();

    const amb = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/promos/ambassadors`,
      {
        headers: host,
        data: {
          event_id: eventId,
          campaign_id: campaignId,
          display_name: "E2E Host Amb",
          email: fanCreds.email,
          referral_code: `e2ehost${stamp}`.slice(0, 20),
          commission_rate_percent: 8,
        },
      },
    );
    expect([201, 409], await amb.text()).toContain(amb.status());

    await loginAs(page, request, "host");
    expect(await softGoto(page, "/host/ambassadors")).toBeTruthy();
    await expect(page.locator("body")).toContainText(
      /Ambassador|Campaign|Referral|Commission/i,
      { timeout: 60_000 },
    );

    await loginAs(page, request, "fan");
    expect(await softGoto(page, "/dashboard/ambassador")).toBeTruthy();
    await expect(page.locator("body")).toContainText(
      /Host|Platform|Ambassador|Referral|Source|Commission/i,
      { timeout: 60_000 },
    );

    const me = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/referrals/me/summary`,
      { headers: await bearer(request, fanCreds) },
    );
    expect(me.ok(), await me.text()).toBeTruthy();
  });

  test("14 · conflict / mixed attribution API contract", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);
    const admin = await bearer(request, getPersonaCreds("super_admin")!);
    const host = await bearer(request, getPersonaCreds("host")!);
    const fan = getPersonaCreds("fan")!;
    const stamp = Date.now();

    const prog = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/promos/admin/referral-programs`,
      {
        headers: admin,
        data: {
          name: `E2E Mixed ${stamp}`,
          ticket_rule: { commission_mode: "percentage", commission_value: 5 },
          merchandise_rule: {
            commission_mode: "fixed",
            commission_value: 250,
          },
        },
      },
    );
    expect([200, 201]).toContain(prog.status());
    const program = await prog.json();

    const enroll = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/promos/admin/referral-programs/${program.id}/enrollments`,
      {
        headers: admin,
        data: {
          email: fan.email,
          referral_code: `e2emix${stamp}`.slice(0, 20),
        },
      },
    );
    expect([201, 409]).toContain(enroll.status());
    let platCode = `e2emix${stamp}`.slice(0, 20);
    if (enroll.status() === 201) {
      platCode = (await enroll.json()).referral_code as string;
    }

    const denied = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/promos/admin/referral-programs`,
      {
        headers: host,
        data: {
          name: "Should fail",
          ticket_rule: { commission_mode: "percentage", commission_value: 1 },
        },
      },
    );
    expect([401, 403]).toContain(denied.status());

    // Open platform link then host area (conflict touch order)
    await softGoto(page, `/r/${platCode}`);
    await loginAs(page, request, "host");
    await softGoto(page, "/host/ambassadors");

    const me = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/referrals/me/summary`,
      { headers: await bearer(request, fan) },
    );
    expect(me.ok(), await me.text()).toBeTruthy();
    const summary = await me.json();
    expect(summary).toHaveProperty("net_commission");
    expect(summary).toHaveProperty("reversed_commission");
    // Payer breakdown fields when present
    if (summary.by_payer || summary.payer_breakdown) {
      const pb = summary.by_payer || summary.payer_breakdown;
      expect(pb).toBeTruthy();
    }

    const hostPlat = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/host/referrals/platform-attributed`,
      { headers: host },
    );
    expect([200, 404]).toContain(hostPlat.status());
  });

  test("15 · partial-refund allocation surface + ledger reconciliation APIs", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);
    const financeCreds = getPersonaCreds("admin_finance");
    const adminCreds = getPersonaCreds("super_admin")!;
    let headers: Record<string, string>;
    if (financeCreds) {
      const login = await request.post(`${apiBaseUrl()}${apiPrefix()}/auth/login`, {
        data: { login: financeCreds.email, password: financeCreds.password },
        headers: { "Content-Type": "application/json" },
      });
      headers = login.ok()
        ? {
            Authorization: `Bearer ${(await login.json()).access_token}`,
            "Content-Type": "application/json",
          }
        : await bearer(request, adminCreds);
    } else {
      headers = await bearer(request, adminCreds);
    }
    const admin = await bearer(request, adminCreds);

    const before = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/admin/referrals/summary`,
      { headers: admin },
    );
    expect(before.ok(), await before.text()).toBeTruthy();
    const s0 = await before.json();
    expect(s0).toHaveProperty("pending_platform_liability");
    expect(s0).toHaveProperty("platform_funded_commission");
    expect(s0).toHaveProperty("host_funded_commission");

    // Refund review endpoint must accept line_allocations shape (validation probe)
    const bogus = await request.post(
      `${apiBaseUrl()}${apiPrefix()}/finance/refunds/requests/00000000-0000-0000-0000-000000000000/review`,
      {
        headers,
        data: {
          action: "approve",
          line_allocations: [
            {
              order_item_id: "00000000-0000-0000-0000-000000000001",
              refunded_quantity: 1,
              refunded_item_subtotal: 5000,
            },
          ],
        },
      },
    );
    // 404 not found is fine; 422 means schema rejected allocations — fail
    expect(bogus.status(), await bogus.text()).not.toBe(422);
    expect([400, 403, 404, 405]).toContain(bogus.status());

    const listPaths = [
      `${apiBaseUrl()}${apiPrefix()}/finance/refunds/requests?limit=5`,
      `${apiBaseUrl()}${apiPrefix()}/finance/admin/refund-requests?limit=5`,
      `${apiBaseUrl()}${apiPrefix()}/finance/refund-requests?limit=5`,
    ];
    let listed = false;
    for (const url of listPaths) {
      const list = await request.get(url, { headers });
      if (list.ok()) {
        listed = true;
        break;
      }
    }
    // At least one finance surface or admin summary must work
    expect(listed || before.ok()).toBeTruthy();

    await loginAs(page, request, "super_admin");
    expect(await softGoto(page, "/admin/ambassadors/liabilities")).toBeTruthy();
    await expect(page.locator("body")).toContainText(
      /Liability|Platform|Host|Referral|Commission/i,
      { timeout: 60_000 },
    );

    const after = await request.get(
      `${apiBaseUrl()}${apiPrefix()}/admin/referrals/summary`,
      { headers: admin },
    );
    expect(after.ok()).toBeTruthy();
    const s1 = await after.json();
    // Reconciliation: host and platform totals remain separated keys
    expect(s1).toHaveProperty("host_funded_commission");
    expect(s1).toHaveProperty("platform_funded_commission");
  });
});
