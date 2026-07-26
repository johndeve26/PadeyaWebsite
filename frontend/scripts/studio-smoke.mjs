/**
 * Event Studio smoke checks — no browser required.
 * Run: npm run test:studio
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

// --- Routes load (pages exist and wire EventStudio) ---
const studioRoutes = [
  "src/app/host/events/new/page.tsx",
  "src/app/host/events/[id]/edit/page.tsx",
  "src/app/host/events/[id]/page.tsx",
  "src/app/host/events/[id]/preview/page.tsx",
];
for (const rel of studioRoutes) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const newPage = read("src/app/host/events/new/page.tsx");
assert.match(newPage, /EventStudio/);
assert.match(newPage, /mode="create"/);
assert.match(newPage, /onSubmitReview/);

const editPage = read("src/app/host/events/[id]/edit/page.tsx");
assert.match(editPage, /EventStudio/);
assert.match(editPage, /eventToStudioValues/);
assert.match(editPage, /updateEvent/);

// --- Core Studio modules ---
const studioModules = [
  "src/components/events/studio/EventStudio.tsx",
  "src/components/events/studio/EventStudioShell.tsx",
  "src/components/events/studio/EventStudioStepper.tsx",
  "src/components/events/studio/EventPreviewPanel.tsx",
  "src/components/events/studio/LocationPrivacySelector.tsx",
  "src/components/events/studio/PublishChecklist.tsx",
  "src/components/events/studio/types.ts",
  "src/components/events/studio/index.ts",
];
for (const rel of studioModules) {
  assert.ok(exists(rel), `missing ${rel}`);
}

// --- Stepper renders canonical steps ---
const types = read("src/components/events/studio/types.ts");
assert.match(types, /export const STUDIO_STEPS/);
for (const step of [
  "basics",
  "location",
  "schedule",
  "tickets",
  "media",
  "lineup",
  "questions",
  "policies",
  "seo",
  "publish",
]) {
  assert.match(types, new RegExp(`id: "${step}"`));
}

const stepper = read("src/components/events/studio/EventStudioStepper.tsx");
assert.match(stepper, /export function EventStudioStepper/);
assert.match(stepper, /STUDIO_STEPS/);
assert.match(stepper, /orientation/);
assert.match(stepper, /current/);

const shell = read("src/components/events/studio/EventStudioShell.tsx");
assert.match(shell, /EventStudioStepper/);
assert.doesNotMatch(shell, /EventPreviewPanel/);
assert.doesNotMatch(shell, /Guest preview/);

// Full guest preview opens in a new tab from Event Studio (not an inline sidebar)
const studioPreview = read("src/components/events/studio/EventStudio.tsx");
assert.match(studioPreview, /window\.open/);
assert.match(studioPreview, /\/host\/events\/\$\{saved\.id\}\/preview/);

// --- Preview panel component kept for reuse / tests ---
const preview = read("src/components/events/studio/EventPreviewPanel.tsx");
assert.match(preview, /export function EventPreviewPanel/);
assert.match(preview, /values/);

// --- Location privacy selector renders ---
const privacy = read("src/components/events/studio/LocationPrivacySelector.tsx");
assert.match(privacy, /export function LocationPrivacySelector/);
assert.match(privacy, /LOCATION_VISIBILITY_OPTIONS/);
assert.match(privacy, /Exact public/);
assert.match(privacy, /Approximate area only/);
assert.match(privacy, /Hidden until ticket purchase/);
assert.match(privacy, /Online \/ no physical venue/);
assert.match(privacy, /REVEAL_TIMING_OPTIONS/);
assert.match(privacy, /onChange/);

// Wired into Studio location step
const studio = read("src/components/events/studio/EventStudio.tsx");
assert.match(studio, /EventStudioShell/);
assert.match(studio, /LocationStep/);
assert.ok(exists("src/components/events/studio/steps/MediaStep.tsx"));
const mediaStep = read("src/components/events/studio/steps/MediaStep.tsx");
assert.match(mediaStep, /MediaPreviewUploader/);
assert.doesNotMatch(mediaStep, /Live previews/);
const mediaUploader = read("src/components/events/studio/MediaPreviewUploader.tsx");
assert.doesNotMatch(mediaUploader, /MediaStudioPreviews/);
assert.doesNotMatch(mediaUploader, /Live previews/);
assert.match(mediaUploader, /MediaUploadThumbnail|No image yet/);
assert.ok(exists("src/components/events/studio/steps/LocationStep.tsx"));
assert.match(read("src/components/events/studio/steps/LocationStep.tsx"), /LocationPrivacySelector/);
assert.match(read("src/components/events/studio/steps/LocationStep.tsx"), /LocationMapFields/);
assert.ok(exists("src/components/events/studio/LocationMapFields.tsx"));
assert.ok(exists("src/components/events/MapPreviewCard.tsx"));
assert.ok(exists("src/components/events/PlacesAutocompleteInput.tsx"));
const mapFields = read("src/components/events/studio/LocationMapFields.tsx");
assert.match(mapFields, /PlacesAutocompleteInput/);
assert.match(mapFields, /Open map preview/);
assert.match(mapFields, /Advanced location details/);
assert.match(mapFields, /Map location is ready/);
assert.match(mapFields, /ensureTaxonomyFromPlaceHints/);
assert.doesNotMatch(mapFields, /Coordinates ready for map/);
assert.ok(exists("src/lib/taxonomy-resolve-place.ts"));
const locationStepSlim = read("src/components/events/studio/steps/LocationStep.tsx");
assert.match(locationStepSlim, /Place on Pàdéyá taxonomy|LocationTaxonomyFields/);
assert.doesNotMatch(
  locationStepSlim,
  /label="Area"[\s\S]*label="City"[\s\S]*label="State"[\s\S]*label="Country"/,
);
assert.ok(exists("src/components/events/studio/LocationPublicPreview.tsx"));
assert.ok(exists("src/lib/location-studio-preview.ts"));
assert.ok(exists("src/lib/location-studio.test.ts"));
const locationStep = read("src/components/events/studio/steps/LocationStep.tsx");
assert.match(locationStep, /LocationPublicPreview/);
assert.match(locationStep, /Directions \/ arrival note/);
assert.ok(exists("src/lib/google-maps.ts"));
assert.match(read("src/lib/event-maps.ts"), /getGoogleMapsApiKey|embed\/v1\/place/);
assert.ok(exists("src/components/events/EventLocationMapCard.tsx"));
assert.ok(exists("src/components/events/RelatedDiscoverySection.tsx"));

// --- Mobile layout does not break (responsive shell) ---
assert.match(shell, /lg:hidden/);
assert.match(shell, /hidden.*lg:block/);
assert.match(shell, /lg:grid-cols-\[250px_minmax\(0,1fr\)\]/);
assert.match(shell, /orientation="horizontal"/);
assert.match(shell, /orientation="vertical"/);
assert.match(shell, /min-w-0/);

// SEO scrub helper used by public metadata
assert.ok(exists("src/lib/seo/event-metadata.ts"));
const seo = read("src/lib/seo/event-metadata.ts");
assert.match(seo, /scrubPrivateAddress/);
assert.match(seo, /location_address_revealed/);

console.log("studio-smoke: ok");
