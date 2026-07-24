/**
 * Vault Studio / public / buyer smoke checks — no browser required.
 * Run: npm run test:vault
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

// --- Host Vault Studio loads ---
const studioRoutes = [
  "src/app/host/vault/page.tsx",
  "src/app/host/vault/new/page.tsx",
  "src/app/host/vault/[id]/edit/page.tsx",
  "src/app/host/vault/[id]/page.tsx",
  "src/app/host/vault/preview/page.tsx",
  "src/app/host/vault/earnings/page.tsx",
];
for (const rel of studioRoutes) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const studioPage = read("src/app/host/vault/page.tsx");
assert.match(studioPage, /VaultStudioShell/);
assert.match(studioPage, /fetchVaultStudio/);
assert.match(studioPage, /VaultStudioItemCard/);

const studioShell = read("src/components/vault/studio/VaultStudioShell.tsx");
assert.match(studioShell, /export function VaultStudioShell/);
assert.match(studioShell, /RequireHost/);
assert.match(studioShell, /DashboardShell/);
assert.match(studioShell, /\/host\/vault\/new/);

// --- Vault create flow renders ---
const newPage = read("src/app/host/vault/new/page.tsx");
assert.match(newPage, /VaultCreator/);

const creatorModules = [
  "src/components/vault/studio/creator/VaultCreator.tsx",
  "src/components/vault/studio/creator/VaultCreatorStepper.tsx",
  "src/components/vault/studio/creator/types.ts",
  "src/components/vault/studio/creator/steps/ContentStep.tsx",
  "src/components/vault/studio/creator/steps/MediaStep.tsx",
  "src/components/vault/studio/creator/steps/AccessStep.tsx",
  "src/components/vault/studio/creator/steps/RelatedEventStep.tsx",
  "src/components/vault/studio/creator/steps/PreviewPublishStep.tsx",
];
for (const rel of creatorModules) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const creatorTypes = read("src/components/vault/studio/creator/types.ts");
assert.match(creatorTypes, /export const VAULT_CREATOR_STEPS/);
for (const step of ["content", "media", "access", "related", "publish"]) {
  assert.match(creatorTypes, new RegExp(`id: "${step}"`));
}

const creator = read("src/components/vault/studio/creator/VaultCreator.tsx");
assert.match(creator, /export function VaultCreator/);
assert.match(creator, /VaultCreatorStepper/);
assert.match(creator, /VAULT_CREATOR_STEPS/);
assert.match(creator, /ContentStep|MediaStep|AccessStep/);

// --- Public Vault page renders locked/unlocked states ---
const publicCatalog = "src/app/u/[username]/vault/page.tsx";
const publicDetail = "src/app/u/[username]/vault/[itemSlug]/page.tsx";
assert.ok(exists(publicCatalog), `missing ${publicCatalog}`);
assert.ok(exists(publicDetail), `missing ${publicDetail}`);

const catalogPage = read(publicCatalog);
assert.match(catalogPage, /PublicVaultItemCard/);
assert.match(catalogPage, /lockedCount|unlockedCount|locked/);
assert.match(catalogPage, /fetchPublicVault|fetchLegacyPage/);

const detailPage = read(publicDetail);
assert.match(detailPage, /VaultItemLockedPanel/);
assert.match(detailPage, /VaultItemUnlockedContent/);
assert.match(detailPage, /item\.locked/);
assert.match(detailPage, /Locked|Unlocked/);

const lockedPanel = read("src/components/vault/public/VaultItemLockedPanel.tsx");
assert.match(lockedPanel, /export function VaultItemLockedPanel/);
assert.match(lockedPanel, /Locked preview|Protected by/);

const unlockedContent = read(
  "src/components/vault/public/VaultItemUnlockedContent.tsx",
);
assert.match(unlockedContent, /export function VaultItemUnlockedContent/);
assert.match(unlockedContent, /Unlocked/);

const publicCard = read("src/components/vault/public/PublicVaultItemCard.tsx");
assert.match(publicCard, /item\.locked/);
assert.match(publicCard, /Locked|Unlocked/);

// --- Buyer Vault page loads ---
const buyerPage = "src/app/dashboard/vault/page.tsx";
assert.ok(exists(buyerPage), `missing ${buyerPage}`);
const buyer = read(buyerPage);
assert.match(buyer, /DashboardShell/);
assert.match(buyer, /fetchMyVaultLibrary/);
assert.match(buyer, /BuyerVaultLibraryCard/);

const buyerCard = read("src/components/vault/buyer/BuyerVaultLibraryCard.tsx");
assert.match(buyerCard, /export function BuyerVaultLibraryCard/);

// --- Mobile layout works (responsive breakpoints present) ---
assert.match(creator, /lg:grid-cols-/);
assert.match(creator, /sm:flex-row|sm:px-/);
assert.match(catalogPage, /sm:grid-cols-2|lg:grid-cols-3/);
assert.match(catalogPage, /sm:flex-row|sm:text-/);
assert.match(detailPage, /lg:grid-cols-|sm:min-h-/);
assert.match(buyer, /sm:|md:|lg:/);
assert.match(studioShell, /flex-wrap/);

// API client surface used by pages
const api = read("src/lib/vault-api.ts");
assert.match(api, /fetchVaultStudio/);
assert.match(api, /createHostVaultItem/);
assert.match(api, /fetchPublicVault/);
assert.match(api, /fetchPublicVaultItem/);
assert.match(api, /fetchMyVaultLibrary/);

console.log("vault-smoke: ok");
