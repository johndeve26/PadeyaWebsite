/**
 * Admin Fee Settings UI smoke checks.
 * Run: node scripts/admin-fees-smoke.mjs
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

assert.ok(exists("src/app/admin/finance/page.tsx"), "finance overview");
assert.ok(exists("src/app/admin/finance/fees/page.tsx"), "fees list");
assert.ok(exists("src/app/admin/finance/fees/new/page.tsx"), "fees create");
assert.ok(
  exists("src/app/admin/finance/fees/[feeId]/page.tsx"),
  "fees edit",
);
assert.ok(
  exists("src/app/admin/finance/host-overrides/page.tsx"),
  "host overrides",
);
assert.ok(
  exists("src/app/admin/hosts/[hostId]/fees/page.tsx"),
  "per-host fees",
);
assert.ok(exists("src/app/admin/finance/earnings/page.tsx"), "earnings");

const feesPage = read("src/app/admin/finance/fees/page.tsx");
assert.match(feesPage, /admin\.finance\.view_fees/);
assert.match(feesPage, /admin\.finance\.manage_fees/);
assert.match(feesPage, /FeePreviewCalculator/);
assert.match(feesPage, /Create fee/);
assert.match(feesPage, /PAYER_COPY/);

const payerCopy = read("src/lib/types/fees.ts");
assert.match(payerCopy, /Buyer-paid fees increase buyer total/);
assert.match(payerCopy, /Host-paid fees reduce host earnings/);
assert.match(payerCopy, /Platform-absorbed fees reduce platform margin/);

const previewUi = read("src/components/admin/FeePreviewCalculator.tsx");
assert.match(previewUi, /Fee preview calculator/);
assert.match(previewUi, /Buyer total/);
assert.match(previewUi, /Host net/);
assert.match(previewUi, /Platform revenue/);

const createPage = read("src/app/admin/finance/fees/new/page.tsx");
assert.match(createPage, /createFeeSetting/);
assert.match(createPage, /admin\.finance\.manage_fees/);
assert.match(createPage, /Unauthorized|Missing permission/);

const editPage = read("src/app/admin/finance/fees/[feeId]/page.tsx");
assert.match(editPage, /updateFeeSetting/);
assert.match(editPage, /Disable fee/);
assert.match(editPage, /admin\.finance\.manage_fees/);

const overridesPage = read("src/app/admin/finance/host-overrides/page.tsx");
assert.match(overridesPage, /createHostFeeOverride/);
assert.match(overridesPage, /admin\.finance\.manage_host_overrides/);
assert.match(overridesPage, /Add override/);

const hostFees = read("src/app/admin/hosts/[hostId]/fees/page.tsx");
assert.match(hostFees, /Active global fees/);
assert.match(hostFees, /Host overrides/);
assert.match(hostFees, /FeePreviewCalculator/);
assert.match(hostFees, /createHostFeeOverride/);

const preview = read("src/lib/fee-preview.ts");
assert.match(preview, /previewFees/);
assert.match(preview, /platform_revenue_minor/);
assert.match(preview, /Math\.round/);
assert.doesNotMatch(preview, /parseFloat\(/);

const api = read("src/lib/fees-api.ts");
assert.match(api, /\/finance\/admin\/fees\/settings/);
assert.match(api, /\/finance\/admin\/fees\/overrides/);

const nav = read("src/lib/nav/workspace.ts");
assert.match(nav, /\/admin\/finance\/fees/);
assert.match(nav, /Host fee overrides/);
assert.match(nav, /\/admin\/finance\/earnings/);

const form = read("src/components/admin/FeeSettingForm.tsx");
assert.match(form, /percentage/);
assert.match(form, /fixed/);
assert.match(form, /mixed/);
assert.match(form, /FEE_PAYER_OPTIONS/);
assert.match(form, /Notes \/ internal reason/);

assert.match(payerCopy, /Buyer pays/);
assert.match(payerCopy, /Host pays/);
assert.match(payerCopy, /Platform absorbs/);

const subnav = read("src/components/admin/AdminFinanceSubnav.tsx");
assert.match(subnav, /Overview/);
assert.match(subnav, /Fees/);
assert.match(subnav, /Host overrides/);
assert.match(subnav, /Earnings/);
assert.match(subnav, /Payouts/);

console.log("admin-fees-smoke: ok");
