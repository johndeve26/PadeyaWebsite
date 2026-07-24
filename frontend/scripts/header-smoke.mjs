/**
 * Public header redesign smoke.
 * Run: npm run test:header
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

for (const rel of [
  "src/components/layout/SiteHeader.tsx",
  "src/components/layout/headerNav.ts",
  "src/components/layout/HeaderDropdown.tsx",
  "src/components/layout/HeaderResourcesDropdown.tsx",
  "src/components/layout/ResourcesMegaPanel.tsx",
  "src/components/layout/HeaderUserMenu.tsx",
  "src/components/layout/HeaderWorkspaceButton.tsx",
  "src/components/layout/HeaderMobileDrawer.tsx",
  "src/components/layout/SiteFooter.tsx",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const header = read("src/components/layout/SiteHeader.tsx");
const nav = read("src/components/layout/headerNav.ts");
const resources = read("src/components/layout/HeaderResourcesDropdown.tsx");
const mega = read("src/components/layout/ResourcesMegaPanel.tsx");
const userMenu = read("src/components/layout/HeaderUserMenu.tsx");
const mobile = read("src/components/layout/HeaderMobileDrawer.tsx");
const cta = read("src/components/layout/CreateEventCta.tsx");
const footer = read("src/components/layout/SiteFooter.tsx");
const dropdown = read("src/components/layout/HeaderDropdown.tsx");

assert.match(nav, /PUBLIC_NAV/);
assert.match(nav, /RESOURCES_NAV/);
assert.match(nav, /RESOURCES_LEARN/);
assert.match(nav, /RESOURCES_SUPPORT/);
assert.match(nav, /RESOURCES_PLATFORM/);
assert.match(nav, /RESOURCES_FEATURED/);
for (const href of ["/events", "/hosts", "/fans", "/merch"]) {
  assert.match(nav, new RegExp(`href: "${href.replace("/", "\\/")}"`));
}
assert.match(nav, /SPONSORSHIP_MARKETPLACE_PATH/);

// Shop is top-level; Merch Guide is Resources-only
const publicNavBlock = nav.slice(
  nav.indexOf("export const PUBLIC_NAV"),
  nav.indexOf("export const RESOURCES_LEARN"),
);
assert.match(publicNavBlock, /href: "\/merch"/);
assert.match(publicNavBlock, /label: "Shop"/);
assert.doesNotMatch(publicNavBlock, /merch-guide/);
assert.doesNotMatch(publicNavBlock, /href: "\/blog"/);
assert.doesNotMatch(publicNavBlock, /href: "\/support"/);
assert.doesNotMatch(publicNavBlock, /href: "\/pricing"/);

for (const href of [
  "/blog",
  "/help",
  "/support",
  "/faq",
  "/pricing",
  "/safety",
  "/contact",
  "/for-hosts",
  "/for-fans",
  "/merch-guide",
  "/report",
  "/community-guidelines",
  "/host/onboarding",
  "/ambassadors",
]) {
  assert.match(
    nav,
    new RegExp(`href: "${href.replace("/", "\\/")}"`),
    `Resources should include ${href}`,
  );
}

assert.match(nav, /isResourcesNavActive/);
assert.match(nav, /\/merch-guide/);
assert.match(nav, /pathname\.startsWith\("\/u\/"\)/);
assert.match(nav, /pathname\.startsWith\("\/f\/"\)/);
assert.match(nav, /case "\/merch"/);
assert.doesNotMatch(
  nav.slice(nav.indexOf('case "/hosts"'), nav.indexOf('case "/fans"')),
  /for-hosts/,
);
assert.doesNotMatch(
  nav.slice(nav.indexOf('case "/fans"'), nav.indexOf("case SPONSORSHIP_MARKETPLACE_PATH")),
  /for-fans/,
);

assert.match(header, /HeaderResourcesDropdown/);
assert.match(header, /HeaderUserMenu/);
assert.match(header, /HeaderMobileDrawer/);
assert.match(header, /CreateEventCta/);
assert.match(header, /ThemeToggle/);
assert.match(header, /Log in/);

// Scrolled marketing header: opaque bar; transparent-on-dark only at scroll top
assert.match(header, /overDark && !scrolled/);
assert.match(header, /showScrolledBar/);
assert.match(header, /bg-card\/95.*backdrop-blur-md/);
assert.doesNotMatch(header, /showGlass/);
assert.doesNotMatch(header, /HeaderWorkspaceButton/);
assert.doesNotMatch(header, /user\.full_name/);

// Mega menu: hover + click, delay close, Escape, outside click, keyboard
assert.match(resources, /ResourcesMegaPanel/);
assert.match(resources, /Escape/);
assert.match(resources, /mousedown/);
assert.match(resources, /aria-haspopup="menu"/);
assert.match(resources, /onMouseEnter/);
assert.match(resources, /onMouseLeave/);
assert.match(resources, /CLOSE_DELAY_MS|setTimeout/);
assert.match(resources, /ArrowDown/);
assert.match(resources, /getBoundingClientRect/);
assert.match(resources, /triggerCenterX|panelWidth \/ 2/);
assert.match(resources, /triggerRect\.bottom|PANEL_GAP_PX/);
assert.doesNotMatch(mega, /left-0|right-0/);
assert.doesNotMatch(mega, /absolute z-50 mt-2/);
assert.match(mega, /resources-panel-gap/);

assert.match(mega, /RESOURCES_LEARN/);
assert.match(mega, /RESOURCES_SUPPORT/);
assert.match(mega, /RESOURCES_PLATFORM/);
assert.match(mega, /RESOURCES_FEATURED/);
assert.match(mega, /RESOURCES_FEATURED\.title/);
assert.match(mega, /Explore Merch|RESOURCES_FEATURED\.cta/);
assert.match(mega, /RESOURCES_FEATURED\.cta\.href/);
assert.match(mega, /bg-ink/);
assert.match(nav, /Sell more than tickets/);
assert.match(nav, /Explore Merch/);
assert.doesNotMatch(mega, /xl:hidden/); // desktop-only via header nav

assert.match(userMenu, /Personal dashboard/);
assert.match(userMenu, /Host workspace/);
assert.match(userMenu, /Admin panel/);
assert.match(userMenu, /Tickets/);
assert.match(userMenu, /Messages/);
assert.match(userMenu, /Settings/);
assert.match(userMenu, /Support/);
assert.match(userMenu, /Log out/);
assert.match(userMenu, /hasHostWorkspace/);
assert.match(userMenu, /isAdmin/);
assert.doesNotMatch(userMenu, /full_name\.split/);

assert.match(mobile, /Discover/);
assert.match(mobile, /Learn/);
assert.match(mobile, /Support/);
assert.match(mobile, /Account/);
assert.match(mobile, /MOBILE_LEARN_NAV/);
assert.match(mobile, /MOBILE_SUPPORT_NAV/);
assert.match(mobile, /CreateEventCta/);
assert.match(mobile, /overflow-x-hidden/);
assert.match(mobile, /Escape/);
assert.match(mobile, /xl:hidden/); // hamburger drawer only — no desktop mega menu
assert.doesNotMatch(mobile, /ResourcesMegaPanel/);

assert.match(cta, /Create event/);
assert.match(cta, /\/host\/events\/new/);
assert.match(cta, /\/host\/onboarding/);
assert.match(cta, /login\?next=\/host\/onboarding/);

assert.match(dropdown, /Escape/);
assert.match(dropdown, /mousedown/);

// Footer
assert.match(footer, /href: "\/fans"/);
assert.match(footer, /Discover/);
assert.match(footer, /For Fans/);
assert.match(footer, /For Hosts/);
assert.match(footer, /Ready for your next night/);
assert.match(footer, /Explore events/);
assert.match(footer, /FooterRoleCta|Admin panel|Host workspace|Personal dashboard/);
assert.match(footer, /footer-mobile-accordion|FooterAccordionSection/);
assert.match(footer, /\/dashboard\/passport/);
assert.match(footer, /Host directory/);
assert.match(footer, /Become a host/);
assert.match(footer, /href: "\/merch"/);
assert.match(footer, /label: "Shop"/);
assert.match(footer, /href: "\/merch-guide"/);
assert.match(footer, /\/dashboard\/merchandise/);
assert.match(footer, /label: "My merch"/);
assert.match(footer, /\/host\/merchandise/);
assert.match(footer, /Merch Studio/);
assert.match(footer, /#8EF012|hover:text-\[#8EF012\]/);
assert.doesNotMatch(footer, /legal review|policy draft|AI-generated/i);

// Support once in Resources Support column (not duplicated as top-level)
const supportCol = nav.slice(
  nav.indexOf("export const RESOURCES_SUPPORT"),
  nav.indexOf("export const RESOURCES_PLATFORM"),
);
assert.equal(
  (supportCol.match(/href: "\/support"/g) || []).length,
  1,
  "Support must appear once in Resources Support column",
);
assert.doesNotMatch(publicNavBlock, /href: "\/support"/);

// Shop marketplace is top-level; Learn/Support/Platform columns must not list /merch
assert.doesNotMatch(
  nav.slice(
    nav.indexOf("export const RESOURCES_LEARN"),
    nav.indexOf("export const RESOURCES_FEATURED"),
  ),
  /href: "\/merch"/,
);
assert.match(nav, /RESOURCES_FEATURED[\s\S]*href: "\/merch"/);

console.log("header-smoke: ok");
