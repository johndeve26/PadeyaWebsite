/**
 * Events Calendar View smoke checks — no browser required.
 * Run: node scripts/events-calendar-smoke.mjs
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
  "src/components/events/discovery/MarketplaceCalendarView.tsx",
  "src/components/events/discovery/EventCalendarDateStrip.tsx",
  "src/components/events/discovery/EventCalendarDayPanel.tsx",
  "src/components/events/discovery/EventCalendarMonth.tsx",
  "src/components/events/discovery/CalendarDayDensityDots.tsx",
  "src/components/events/discovery/calendar-day-chrome.ts",
  "src/lib/events/calendar-grouping.ts",
  "src/app/events/calendar/page.tsx",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const listing = read("src/lib/events/marketplace-listing.ts");
assert.match(listing, /"calendar"/);
assert.match(listing, /raw === "calendar"/);

const results = read("src/components/events/marketplace/EventsResults.tsx");
assert.match(results, /view === "calendar"/);
assert.match(results, /MarketplaceCalendarView/);
assert.match(results, /dateFilterActive/);
assert.match(results, /onClearDateFilter/);

const calendarPage = read("src/app/events/calendar/page.tsx");
assert.match(calendarPage, /permanentRedirect/);
assert.match(calendarPage, /\/events\?view=calendar/);

const grouping = read("src/lib/events/calendar-grouping.ts");
assert.match(grouping, /export function weekGridRows/);
assert.match(grouping, /export function sundayOf/);
assert.match(grouping, /export function dateInWeekWindow/);

const strip = read(
  "src/components/events/discovery/EventCalendarDateStrip.tsx",
);
assert.match(strip, /CalendarDayDensityDots/);
assert.match(strip, /calendarStripDayClass/);
assert.match(strip, /weekGridRows/);
assert.match(strip, /WEEK_COUNT_MOBILE = 2/);
assert.match(strip, /WEEK_COUNT_DESKTOP = 3/);
assert.match(strip, /grid-cols-7/);
assert.match(strip, /useVisibleWeekCount/);
assert.doesNotMatch(strip, /overflow-x-auto/);
assert.doesNotMatch(strip, /bg-primary text-primary-foreground/);
assert.doesNotMatch(strip, /CalendarDayEventThumbs/);

const panel = read(
  "src/components/events/discovery/EventCalendarDayPanel.tsx",
);
assert.match(panel, /No events on this day/);
assert.match(panel, /Clear date filter/);
assert.match(panel, /Browse all events/);
assert.match(panel, /aria-live="polite"/);
assert.match(panel, /calendarAgendaPriceClass|text-primary-text dark:text-primary/);
assert.match(panel, /Pàdéyá/);

const chrome = read(
  "src/components/events/discovery/calendar-day-chrome.ts",
);
assert.match(chrome, /ring-primary/);
assert.match(chrome, /bg-ink text-paper/);
assert.match(chrome, /calendarStripDayClass/);
assert.match(chrome, /hasEvents/);
assert.doesNotMatch(chrome, /bg-primary text-primary-foreground/);

const view = read(
  "src/components/events/discovery/MarketplaceCalendarView.tsx",
);
assert.match(view, /EventCalendarDateStrip/);
assert.match(view, /EventCalendarDayPanel/);
assert.match(view, /onClearDateFilter/);
assert.match(view, /adjacentPrev|findAdjacentDayWithEvents/);
assert.match(view, /view=calendar|shiftWeek|-7/);

console.log("events-calendar-smoke: ok");
