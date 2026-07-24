/**
 * Fan Connect smoke checks — no browser / React test runner required.
 * Mirrors vault-smoke / merch-smoke patterns.
 * Run: npm run test:fan-connect
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
    /text-foreground|text-heading|text-muted-foreground|bg-card|border-border/,
    `${rel} should use semantic theme tokens for light/dark`,
  );
  // Fixed --ink stays black under .dark — never use for body copy.
  const withoutInkHero = source.replace(
    /className="[^"]*\bbg-ink\b[\s\S]*?<\/section>/g,
    "",
  );
  assert.doesNotMatch(
    withoutInkHero,
    /\btext-ink\b/,
    `${rel} must not use text-ink on themed surfaces`,
  );
  assert.doesNotMatch(
    withoutInkHero,
    /\btext-muted[^-]/g,
    `${rel} must use text-muted-foreground (not text-muted surface token)`,
  );
}

function assertMobileResponsive(rel, source) {
  assert.match(
    source,
    /sm:|md:|lg:|xl:|max-w-|min-w-0|flex-wrap|w-full/,
    `${rel} should include responsive / mobile-friendly layout classes`,
  );
}

// --- /connect routes load ---
const connectRoutes = [
  "src/app/connect/page.tsx",
  "src/app/connect/suggestions/page.tsx",
  "src/app/connect/requests/page.tsx",
  "src/app/connect/connections/page.tsx",
  "src/app/connect/settings/page.tsx",
  "src/app/connect/events/page.tsx",
  "src/app/connect/layout.tsx",
];
for (const rel of connectRoutes) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const homePage = read("src/app/connect/page.tsx");
assert.match(homePage, /ConnectHome/);
assert.match(homePage, /ConnectShell/);

const suggestionsPage = read("src/app/connect/suggestions/page.tsx");
assert.match(suggestionsPage, /ConnectSuggestions/);
assert.match(suggestionsPage, /ConnectShell/);

const requestsPage = read("src/app/connect/requests/page.tsx");
assert.match(requestsPage, /ConnectRequestList/);
assert.match(requestsPage, /incoming|outgoing/);

const connectionsPage = read("src/app/connect/connections/page.tsx");
assert.match(connectionsPage, /ConnectionsList/);

const settingsPage = read("src/app/connect/settings/page.tsx");
assert.match(settingsPage, /ConnectSettingsForm/);
assert.match(settingsPage, /Private by default|Fan Connect stays off/i);

const layout = read("src/app/connect/layout.tsx");
assert.match(layout, /RequireAuth/);
assert.match(layout, /WorkspaceShell/);

// --- Dashboard aliases load (redirect to /connect/*) ---
const aliases = [
  ["src/app/dashboard/connect/page.tsx", "/connect"],
  ["src/app/dashboard/connect/suggestions/page.tsx", "/connect/suggestions"],
  ["src/app/dashboard/connect/requests/page.tsx", "/connect/requests"],
  ["src/app/dashboard/connect/connections/page.tsx", "/connect/connections"],
  ["src/app/dashboard/connect/settings/page.tsx", "/connect/settings"],
  ["src/app/dashboard/connect/events/page.tsx", "/connect/events"],
];
for (const [rel, target] of aliases) {
  assert.ok(exists(rel), `missing ${rel}`);
  const src = read(rel);
  assert.match(src, /redirect/);
  assert.match(src, new RegExp(target.replace(/\//g, "\\/")));
}

// --- Core components exist ---
const components = [
  "src/components/fan-connect/ConnectShell.tsx",
  "src/components/fan-connect/ConnectHome.tsx",
  "src/components/fan-connect/ConnectSuggestions.tsx",
  "src/components/fan-connect/ConnectRequestList.tsx",
  "src/components/fan-connect/ConnectionsList.tsx",
  "src/components/fan-connect/ConnectSettingsForm.tsx",
  "src/components/fan-connect/FanConnectCard.tsx",
  "src/components/fan-connect/ConnectButton.tsx",
  "src/components/fan-connect/EventFanConnectSection.tsx",
  "src/components/fan-connect/SharedContextChips.tsx",
];
for (const rel of components) {
  assert.ok(exists(rel), `missing ${rel}`);
}

// --- Event Fan Connect section appears only when allowed ---
const eventSection = read(
  "src/components/fan-connect/EventFanConnectSection.tsx",
);
assert.match(eventSection, /export function eventIsPublicSafeForConnect/);
assert.match(eventSection, /export function EventFanConnectSection/);
assert.match(eventSection, /previewMode/);
assert.match(eventSection, /fan_connect_enabled/);
assert.match(eventSection, /kind: "hidden"/);
assert.match(eventSection, /secret_location|invite_only|private/);
assert.match(eventSection, /visibility !== "listed"/);
assert.match(
  read("src/components/events/EventPublicView.tsx"),
  /EventFanConnectSection/,
);

// --- Settings update works ---
const settingsForm = read(
  "src/components/fan-connect/ConnectSettingsForm.tsx",
);
assert.match(settingsForm, /updateFanConnectSettings/);
assert.match(settingsForm, /fan_connect_enabled/);
assert.match(settingsForm, /allow_connection_requests/);
assert.match(settingsForm, /fetchFanConnectSettings/);

// --- Send / accept / decline request works ---
const card = read("src/components/fan-connect/FanConnectCard.tsx");
assert.match(card, /createConnectRequest/);
assert.match(card, /acceptConnectRequest/);
assert.match(card, /declineConnectRequest/);
assert.match(card, /Send request/);
assert.match(card, /Accept/);
assert.match(card, /Decline/);

const connectBtn = read("src/components/fan-connect/ConnectButton.tsx");
assert.match(connectBtn, /createConnectRequest/);
assert.match(connectBtn, /fetchCanConnect/);
assert.match(connectBtn, /Connect requested/);

const requestList = read(
  "src/components/fan-connect/ConnectRequestList.tsx",
);
assert.match(requestList, /acceptConnectRequest/);
assert.match(requestList, /declineConnectRequest/);

// --- Remove / block / report works ---
const connectionsList = read(
  "src/components/fan-connect/ConnectionsList.tsx",
);
assert.match(connectionsList, /removeConnection/);
assert.match(connectionsList, /blockFanConnect/);
assert.match(connectionsList, /reportFanConnect/);

// --- fan_fan message thread only after accepted connection ---
assert.match(card, /cta === "message" && threadId/);
assert.match(card, /\/dashboard\/messages\/\$\{threadId\}/);
assert.match(connectBtn, /connection_status === "connected"/);
assert.match(connectBtn, /\/dashboard\/messages\/\$\{state\.thread_id\}/);
const inbox = read("src/components/messaging/MessagesInbox.tsx");
assert.match(inbox, /thread_type === "fan_fan"|connect_context/);
assert.match(inbox, /Fan Connect/);
const threadItem = read("src/components/messaging/ThreadListItem.tsx");
assert.match(threadItem, /thread_type === "fan_fan"|connect_context/);

// --- Empty states work ---
const home = read("src/components/fan-connect/ConnectHome.tsx");
assert.match(home, /EmptyState/);
assert.match(home, /Fan Connect is off/);
assert.match(read("src/components/fan-connect/ConnectSuggestions.tsx"), /EmptyState/);
assert.match(requestList, /EmptyState/);
assert.match(connectionsList, /EmptyState/);
assert.match(settingsForm, /EmptyState/);

// --- Mobile responsive breakpoints ---
for (const [rel, src] of [
  ["ConnectHome", home],
  ["ConnectSuggestions", read("src/components/fan-connect/ConnectSuggestions.tsx")],
  ["EventFanConnectSection", eventSection],
  ["FanConnectCard", card],
  ["ConnectionsList", connectionsList],
]) {
  assert.match(
    src,
    /sm:|md:|lg:|flex-wrap/,
    `${rel} should include responsive layout classes`,
  );
}

// --- Light / dark mode via brand tokens ---
for (const rel of [
  "src/components/fan-connect/ConnectHome.tsx",
  "src/components/fan-connect/FanConnectCard.tsx",
  "src/components/fan-connect/ConnectSettingsForm.tsx",
  "src/components/fan-connect/EventFanConnectSection.tsx",
  "src/components/fan-connect/ConnectionsList.tsx",
  "src/components/fan-connect/ConnectRequestList.tsx",
]) {
  assertThemeSafeTokens(rel, read(rel));
}

// Theme system still wired for light/dark (Connect inherits app ThemeProvider)
assert.match(read("src/app/layout.tsx"), /ThemeProvider/);
assert.match(read("src/styles/globals.css"), /--ink|--surface|--border|--background|--paper|--primary/);

// --- API client surface ---
const api = read("src/lib/fan-connect-api.ts");
for (const fn of [
  "fetchFanConnectSettings",
  "updateFanConnectSettings",
  "fetchCanConnect",
  "createConnectRequest",
  "fetchConnectRequests",
  "acceptConnectRequest",
  "declineConnectRequest",
  "fetchConnections",
  "removeConnection",
  "blockFanConnect",
  "reportFanConnect",
  "fetchConnectSuggestions",
  "fetchEventFanConnect",
]) {
  assert.match(api, new RegExp(`export async function ${fn}`));
}

// --- Buyer nav exposes Connect ---
assert.match(read("src/lib/nav/workspace.ts"), /href: "\/connect"/);

// --- Passport surface offers Connect for visitors; own CTAs for owner ---
const heroRel = "src/components/passport/FanPassportHero.tsx";
const ctaRel = "src/components/passport/FanPassportCTA.tsx";
const passportCardRel = "src/components/passport/FanPassportCard.tsx";
const dirRel = "src/components/passport/FansDirectory.tsx";
const ownFanLib = "src/lib/own-fan-ctas.ts";

assert.ok(exists(heroRel));
assert.ok(exists(ownFanLib));
const hero = read(heroRel);
const cta = read(ctaRel);
const passportCard = read(passportCardRel);
const directory = read(dirRel);
const ownFan = read(ownFanLib);

assert.match(hero, /ConnectButton/);
assert.match(ownFan, /This is your Fan Passport/);
assert.match(ownFan, /Preview how your public fan identity appears on Pàdéyá/);
assert.match(ownFan, /Edit Passport/);
assert.match(ownFan, /Personal dashboard/);
assert.match(ownFan, /Share profile/);
assert.match(ownFan, /showConnect: false/);
assert.match(ownFan, /showMessage: false/);
assert.match(ownFan, /youBadge: "You"/);
assert.match(hero, /isOwnPassport/);
assert.match(cta, /isOwnPassport/);
assert.match(passportCard, /directoryCardCtas|isOwnFanPassport|youBadge|You/);
assert.match(directory, /FansDirectory|directoryCardCtas|isOwnFanPassport/);

// --- Dark / light + mobile layout on public passport surfaces ---
for (const [rel, source] of [
  [ctaRel, cta],
  [passportCardRel, passportCard],
  [dirRel, directory],
]) {
  assertThemeSafeTokens(rel, source);
  assertMobileResponsive(rel, source);
}
assert.match(hero, /sm:|md:|lg:|flex-wrap/);
assert.match(passportCard, /dark:/);

console.log("fan-connect-smoke: ok");
