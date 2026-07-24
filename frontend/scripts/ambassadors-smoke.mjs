/**
 * Ambassadors smoke checks — no browser / React test runner required.
 * Mirrors merch-smoke / fan-connect-smoke patterns.
 * Run: npm run test:ambassadors
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

function assertThemeSafeTokens(rel, source) {
  assert.match(
    source,
    /text-foreground|text-heading|text-muted-foreground|bg-card|border-border|text-subtle-foreground/,
    `${rel} should use semantic theme tokens for light/dark`,
  );
  const withoutInkHero = source.replace(
    /className="[^"]*\bbg-ink\b[\s\S]*?<\/section>/g,
    "",
  );
  assert.doesNotMatch(
    withoutInkHero,
    /\btext-ink\b/,
    `${rel} must not use text-ink on themed surfaces`,
  );
}

function assertMobileResponsive(rel, source) {
  assert.match(
    source,
    /sm:|md:|lg:|xl:|max-w-|min-w-0|flex-wrap|break-all|w-full/,
    `${rel} should include responsive / mobile-friendly layout classes`,
  );
}

// --- /ambassadors loads ---
const landing = "src/app/ambassadors/page.tsx";
assert.ok(exists(landing), `missing ${landing}`);
const landingSrc = read(landing);
assert.match(landingSrc, /Ambassadors|Pàdéyá/);
assert.match(landingSrc, /EligibleEventsGrid|fetchDomainEligibleEvents|eligible/);
assertThemeSafeTokens(landing, landingSrc);
assertMobileResponsive(landing, landingSrc);

// --- eligible events display ---
const eventsPage = "src/app/ambassadors/events/page.tsx";
const eligibleGrid = "src/components/ambassadors/EligibleEventsGrid.tsx";
assert.ok(exists(eventsPage), `missing ${eventsPage}`);
assert.ok(exists(eligibleGrid), `missing ${eligibleGrid}`);
const gridSrc = read(eligibleGrid);
assert.match(gridSrc, /Promote this event/);
assert.match(gridSrc, /sm:grid-cols-|xl:grid-cols-/);
assert.match(read(eventsPage), /Promote this event|EligibleEventsGrid|eligible/i);

// --- Promote this event CTA appears on event page ---
const promote = "src/components/events/PromoteEventAmbassadors.tsx";
const eventPublic = "src/components/events/EventPublicView.tsx";
assert.ok(exists(promote), `missing ${promote}`);
assert.ok(exists(eventPublic), `missing ${eventPublic}`);
const promoteSrc = read(promote);
assert.match(promoteSrc, /export function PromoteEventAmbassadors/);
assert.match(promoteSrc, /Promote this event|Join|accept_terms|join/i);
assert.match(read(eventPublic), /PromoteEventAmbassadors/);

// --- Join campaign works ---
assert.match(promoteSrc, /joinOpenEventAmbassador|accept_terms/);
assert.match(
  read("src/lib/ambassadors-api.ts"),
  /joinEventAmbassadorBySlug|fetchDomainEligibleEvents|trackAmbassadorClick|fetchDomainEarnings/,
);

// --- referral link/code copy works ---
assert.match(promoteSrc, /navigator\.clipboard\.writeText/);
assert.match(promoteSrc, /Copy link|Copy code/);
const linksPage = "src/app/dashboard/ambassador/links/page.tsx";
assert.ok(exists(linksPage), `missing ${linksPage}`);
const linksSrc = read(linksPage);
assert.match(linksSrc, /navigator\.clipboard\.writeText/);
assert.match(linksSrc, /Copy link|Copy code/);
const shareCard = "src/components/ambassadors/AmbassadorShareCard.tsx";
assert.ok(exists(shareCard), `missing ${shareCard}`);
assert.match(read(shareCard), /export function AmbassadorShareCard/);
assert.match(read(shareCard), /QRCodeSVG|qrcode/);

// --- ambassador dashboard loads ---
const dashRoutes = [
  "src/app/dashboard/ambassador/page.tsx",
  "src/app/dashboard/ambassador/earnings/page.tsx",
  "src/app/dashboard/ambassador/links/page.tsx",
  "src/app/dashboard/ambassador/leaderboard/page.tsx",
  "src/app/dashboard/ambassador/payouts/page.tsx",
  "src/app/dashboard/ambassador/events/page.tsx",
];
for (const rel of dashRoutes) {
  assert.ok(exists(rel), `missing ${rel}`);
  const src = read(rel);
  assert.match(src, /AmbassadorDashNav/);
  assert.match(src, /DashboardShell/);
  // Shell + UI primitives carry theme tokens; pages may only compose them.
  assertMobileResponsive(rel, src);
}

// --- host campaign dashboard loads ---
const hostRoutes = [
  "src/app/host/ambassadors/page.tsx",
  "src/app/host/ambassadors/campaigns/page.tsx",
  "src/app/host/ambassadors/campaigns/new/page.tsx",
  "src/app/host/ambassadors/campaigns/[id]/page.tsx",
  "src/app/host/ambassadors/conversions/page.tsx",
  "src/app/host/ambassadors/payouts/page.tsx",
  "src/app/host/events/[id]/ambassadors/page.tsx",
];
for (const rel of hostRoutes) {
  assert.ok(exists(rel), `missing ${rel}`);
  const src = read(rel);
  assert.match(src, /HostAmbassadorsNav|DashboardShell/);
  assert.match(src, /campaign|Ambassador|conversion|payout/i);
  assertMobileResponsive(rel, src);
}

// --- host reward actions are permission-gated ---
const conversionsSrc = read("src/app/host/ambassadors/conversions/page.tsx");
assertThemeSafeTokens(
  "src/app/host/ambassadors/conversions/page.tsx",
  conversionsSrc,
);
assert.match(conversionsSrc, /hasHostPermission/);
assert.match(conversionsSrc, /ambassadors\.approve_rewards/);
assert.match(conversionsSrc, /ambassadors\.mark_rewards_paid/);
assert.match(conversionsSrc, /Read-only|canApprove|canMarkPaid/);
assert.match(conversionsSrc, /setHostConversionRewardStatus/);
assert.doesNotMatch(
  conversionsSrc,
  /buyer_email|shipping_address|ticket_qr|pickup_qr/,
);
assertThemeSafeTokens(
  "src/app/host/ambassadors/payouts/page.tsx",
  read("src/app/host/ambassadors/payouts/page.tsx"),
);

const teamRolesSrc = read("src/lib/host-team-roles.ts");
assert.match(teamRolesSrc, /ambassadors\.approve_rewards/);
assert.match(teamRolesSrc, /ambassadors\.mark_rewards_paid/);
assert.match(teamRolesSrc, /ambassadors\.reverse_rewards/);
assert.match(
  teamRolesSrc,
  /Reward and payout permissions allow this team member/,
);

const teamToggles = "src/components/hosts/team/TeamPermissionToggles.tsx";
assert.ok(exists(teamToggles), `missing ${teamToggles}`);
assert.match(read(teamToggles), /PERMISSION_GROUPS|group\.hint/);

// --- admin ambassador pages load ---
const adminRoutes = [
  "src/app/admin/ambassadors/page.tsx",
  "src/app/admin/ambassadors/campaigns/page.tsx",
  "src/app/admin/ambassadors/conversions/page.tsx",
  "src/app/admin/ambassadors/fraud/page.tsx",
  "src/app/admin/ambassadors/payouts/page.tsx",
  "src/app/admin/ambassadors/reports/page.tsx",
];
for (const rel of adminRoutes) {
  assert.ok(exists(rel), `missing ${rel}`);
  const src = read(rel);
  assert.match(src, /AdminAmbassadorsNav|DashboardShell/);
  assert.match(src, /Ambassador/i);
  assertMobileResponsive(rel, src);
}

// --- dark/light mode: theme provider still wired (global) ---
assert.ok(exists("src/components/theme/ThemeProvider.tsx"));
assert.ok(exists("src/components/theme/ThemeToggle.tsx"));
assert.match(read("src/app/layout.tsx"), /ThemeProvider/);

// --- how-it-works + nav components ---
assert.ok(exists("src/app/ambassadors/how-it-works/page.tsx"));
assert.ok(exists("src/components/ambassadors/AmbassadorDashNav.tsx"));
assert.ok(exists("src/components/ambassadors/HostAmbassadorsNav.tsx"));
assert.ok(exists("src/components/ambassadors/AdminAmbassadorsNav.tsx"));

console.log("ambassadors-smoke: ok");
