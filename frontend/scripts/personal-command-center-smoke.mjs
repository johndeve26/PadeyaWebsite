/**
 * Personal Command Center (/dashboard) smoke — Phase 3.
 * Run: npm run test:personal-command-center
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

assert.ok(exists("src/components/personal/command-center/PersonalCommandCenter.tsx"));
assert.ok(exists("src/components/personal/command-center/NextUpSection.tsx"));
assert.ok(exists("src/lib/personal-command-center.ts"));

const page = read("src/app/dashboard/page.tsx");
assert.match(page, /PersonalCommandCenter/);
assert.doesNotMatch(
  page,
  /userHasRole|Roles:|Host workspace|Support|Admin/,
  "Command Center home must not dump roles or Support/Admin CTAs",
);

const center = read(
  "src/components/personal/command-center/PersonalCommandCenter.tsx",
);
assert.match(center, /Personal Command Center/);
assert.match(center, /NextUpSection/);
assert.match(center, /MyActivitySection/);
assert.match(center, /CommunitySection/);
assert.match(center, /IdentitySection/);
assert.match(center, /VaultSection/);
assert.match(center, /AmbassadorSection/);
assert.match(center, /QuickActionsSection/);
assert.match(center, /WelcomeEmptySection/);
assert.match(center, /PersonalWorkspaceRoutingCard/);
assert.match(center, /isQuietPersonalHome/);
assert.match(center, /useUnreadMessages/);
assert.match(center, /fetchMyTickets/);
assert.match(center, /fetchMyOrders/);
assert.match(center, /fetchMyMerch/);
assert.match(center, /fetchMyPassport/);
assert.match(center, /fetchMyVaultLibrary/);
assert.match(center, /fetchAmbassadorEarningsSummary/);
assert.match(center, /if \(p0Loading\) return/);
assert.ok(
  center.indexOf("fetchMyTickets") < center.indexOf("fetchMyPassport"),
  "P0 tickets must load before deferred Passport",
);
assert.ok(
  center.indexOf("fetchMyTickets") < center.indexOf("fetchConnectRequests"),
  "P0 tickets must load before deferred Connect",
);
assert.doesNotMatch(
  center,
  /fetchMyBadges/,
  "badges come from passport — no separate badges fetch on home",
);
assert.doesNotMatch(
  center,
  /fetchMyAmbassadorEnrollments/,
  "enrollments signal comes from earnings summary — avoid extra list fetch",
);
assert.doesNotMatch(
  center,
  /for\s*\([^)]*\)[^{]*\{[^}]*fetchReviewEligibility/s,
  "do not N+1 eligibility per ticket",
);
assert.doesNotMatch(
  center,
  /from "@\/components\/hosts\/WorkspaceSwitcher"|<WorkspaceSwitcher/,
  "do not remount workspace switcher in page body",
);
assert.doesNotMatch(
  center,
  /\/host\/desk|\/host\/payouts|\/host\/team|\/admin/,
  "Personal Command Center must not deep-link host desk/finance/team or admin",
);

const nextUp = read("src/components/personal/command-center/NextUpSection.tsx");
assert.match(nextUp, /TicketQrModal/);
assert.match(nextUp, /Open QR/);
assert.match(nextUp, /View ticket/);
assert.match(nextUp, /Ticket details/);
assert.match(nextUp, /Browse events/);
assert.match(nextUp, /Merch ready for pickup/);
assert.match(nextUp, /resolveNextUp/);
assert.match(nextUp, /safeTicketLocationLabel/);
assert.doesNotMatch(
  nextUp,
  /qr_payload/,
  "Next up must not expose raw QR payload — use TicketQrModal",
);

const helpers = read("src/lib/personal-command-center.ts");
assert.match(helpers, /pickNextTicket/);
assert.match(helpers, /resolveNextUp/);
assert.match(helpers, /safeTicketLocationLabel/);
assert.match(helpers, /buildActivityChips/);
assert.match(helpers, /isQuietPersonalHome/);
assert.match(helpers, /hasAttentionSignals/);
assert.match(helpers, /shouldShowCommunityStrip/);
assert.match(helpers, /pickReviewPromptTicket/);

const welcome = read(
  "src/components/personal/command-center/WelcomeEmptySection.tsx",
);
assert.match(welcome, /Welcome to your Personal Command Center/);
assert.match(welcome, /Browse events/);
assert.match(welcome, /Set up Passport/);
assert.match(welcome, /Promote an event/);
assert.match(welcome, /Become a host/);
assert.match(welcome, /variant="ghost"/);
assert.doesNotMatch(welcome, /0 upcoming|0 pending|0 open/);
assert.doesNotMatch(
  welcome,
  /min-h-\[|h-screen|sm:text-2xl|text-3xl|text-4xl|full-bleed/,
  "welcome must stay compact — not a marketing block",
);
assert.match(helpers, /shouldShowAmbassadorStrip/);
assert.match(helpers, /passportVisibilityLabel/);
assert.match(helpers, /Always includes Refunds/);
assert.match(helpers, /openRefundCount/);
assert.match(helpers, /cancelled/);
assert.match(helpers, /refunded/);
assert.match(helpers, /invalid/);

const identity = read(
  "src/components/personal/command-center/IdentitySection.tsx",
);
assert.match(identity, /reviewPrompt|Write review/);
assert.doesNotMatch(identity, /Roles:|userHasRole/);

const ambassador = read(
  "src/components/personal/command-center/AmbassadorSection.tsx",
);
assert.match(ambassador, /Copy links/);
assert.match(ambassador, /View Ambassadors/);

const quick = read(
  "src/components/personal/command-center/QuickActionsSection.tsx",
);
assert.match(quick, /Browse events/);
assert.match(quick, /View tickets/);
assert.match(quick, /Open messages/);
assert.match(quick, /Open Passport/);
assert.match(quick, /Promote an event/);
assert.match(quick, /Become a host/);
assert.match(quick, /\/host\/onboarding/);
assert.match(quick, /sidebar switcher/);
assert.doesNotMatch(quick, /\/support|\/admin/);

// Privacy §12 — scan Command Center tree + helpers for forbidden surfaces/fields
const privacyRoots = [
  "src/components/personal/command-center",
  "src/lib/personal-command-center.ts",
];
const privacyFiles = [];
for (const rel of privacyRoots) {
  const abs = path.join(root, rel);
  const st = fs.statSync(abs);
  if (st.isDirectory()) {
    for (const name of fs.readdirSync(abs)) {
      if (name.endsWith(".tsx") || name.endsWith(".ts")) {
        privacyFiles.push(path.join(rel, name));
      }
    }
  } else {
    privacyFiles.push(rel);
  }
}

const forbidden = [
  [/\/host\/desk/, "host desk / scanner"],
  [/\/host\/payouts/, "host finance"],
  [/\/host\/team/, "host team tools"],
  [/\/host\/audience/, "host audience"],
  [/\/host\/events\/[^"'`]+\/attendees/, "host attendee lists"],
  [/\/host\/events\/[^"'`]+\/check-in/, "host scanner check-in"],
  [/\/staff\/check-in/, "staff scanner"],
  [/["'`]\/admin(?:\/[^"'`]*)?["'`]/, "admin tools"],
  [/["'`]\/support(?:\/[^"'`]*)?["'`]/, "support queues"],
  [/\bqr_payload\b/, "raw QR secrets"],
  [/\bqr_token\b/, "raw merch QR secrets"],
  [/\bauthorization_url\b/, "raw payment provider refs"],
  [/\baccess_code\b/, "raw payment access codes"],
  [/WorkspaceSwitcher/, "duplicate workspace switcher in body"],
  [/fetchHostPayout|fetchHostFinance|fetchDesk/, "host finance/desk fetchers"],
];

for (const rel of privacyFiles) {
  const src = read(rel);
  // Become a host onboarding is allowed
  const scrubbed = src.replaceAll("/host/onboarding", "");
  for (const [pattern, label] of forbidden) {
    assert.doesNotMatch(
      scrubbed,
      pattern,
      `${rel} must not include ${label}`,
    );
  }
}

// Connect on home is count-only (no requester profile dump)
assert.match(
  center,
  /connectRes\.value\.items\.length|connectPending/,
  "Connect pending must be a count for the signed-in user",
);
assert.doesNotMatch(
  read("src/components/personal/command-center/CommunitySection.tsx"),
  /requester_|sender_email|phone|private_note/,
  "Community strip must not render other users’ private Connect fields",
);

// Venue privacy: only safeTicketLocationLabel / location_label — no address inventing
assert.doesNotMatch(
  nextUp,
  /\.address\b|venue_name|location_address_revealed/,
  "Next up must not invent hidden venue/address fields",
);
assert.match(helpers, /safeTicketLocationLabel/);

// Design: tokens + overflow safety + no feature-dump grid
const designFiles = privacyFiles.filter((rel) =>
  rel.includes("command-center/"),
);
for (const rel of designFiles) {
  const src = read(rel);
  assert.doesNotMatch(
    src,
    /#[0-9a-fA-F]{3,8}\b/,
    `${rel} must use design tokens — no hardcoded hex`,
  );
  assert.doesNotMatch(
    src,
    /\b(Inter|Roboto|Arial)\b/,
    `${rel} must not hardcode default font stacks`,
  );
}
assert.match(center, /compact/);
assert.match(center, /min-w-0/);
assert.match(nextUp, /min-w-0/);
assert.match(nextUp, /break-words/);
assert.match(quick, /flex-wrap/);
assert.doesNotMatch(
  quick,
  /grid-cols-[3-9]/,
  "quick actions must not become a feature-dump grid",
);

console.log("personal-command-center-smoke: ok");
