#!/usr/bin/env node
/**
 * Generate premium local demo SVG assets for Pàdéyá.
 * No external images — abstract branded compositions by category.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..", "public", "demo");

const C = {
  green: "#8EF012",
  black: "#000000",
  white: "#FFFFFF",
  soft: "#DDDDDD",
  dark: "#111111",
  gray: "#1A1A1A",
  mid: "#666666",
};

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function uid(prefix, seed) {
  return `${prefix}-${String(seed).replace(/[^a-z0-9]+/gi, "").slice(0, 24)}`;
}

/** Category visual kits — distinct compositions, same brand system */
const KITS = {
  music: {
    label: "MUSIC · NIGHTLIFE",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${C.black}"/>
          <stop offset="55%" stop-color="${C.dark}"/>
          <stop offset="100%" stop-color="${C.gray}"/>
        </linearGradient>
        <radialGradient id="${id}-glow" cx="78%" cy="22%" r="45%">
          <stop offset="0%" stop-color="${C.green}" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="${C.green}" stop-opacity="0"/>
        </radialGradient>
        <linearGradient id="${id}-wave" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="${C.green}" stop-opacity="0"/>
          <stop offset="40%" stop-color="${C.green}" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="${C.green}" stop-opacity="0.15"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <circle cx="920" cy="140" r="260" fill="url(#${id}-glow)"/>
      <g opacity="0.9" stroke="url(#${id}-wave)" stroke-width="3" fill="none">
        <path d="M80 420 C200 300 320 540 440 400 S680 280 800 420 1040 500 1160 380"/>
        <path d="M80 460 C220 340 340 560 460 440 S700 320 820 460 1060 520 1160 420" opacity="0.55"/>
        <path d="M80 500 C240 380 360 580 480 480 S720 360 840 500 1080 540 1160 460" opacity="0.3"/>
      </g>
      <circle cx="980" cy="200" r="88" fill="none" stroke="${C.green}" stroke-opacity="0.35" stroke-width="10"/>
      <circle cx="980" cy="200" r="42" fill="${C.green}" fill-opacity="0.2"/>
      <circle cx="980" cy="200" r="10" fill="${C.green}"/>
      <rect x="0" y="0" width="10" height="100%" fill="${C.green}"/>`;
    },
  },
  comedy: {
    label: "COMEDY",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stop-color="${C.gray}"/>
          <stop offset="100%" stop-color="${C.black}"/>
        </linearGradient>
        <radialGradient id="${id}-spot" cx="35%" cy="0%" r="55%">
          <stop offset="0%" stop-color="${C.white}" stop-opacity="0.18"/>
          <stop offset="55%" stop-color="${C.green}" stop-opacity="0.12"/>
          <stop offset="100%" stop-color="${C.black}" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <ellipse cx="420" cy="-40" rx="280" ry="420" fill="url(#${id}-spot)"/>
      <path d="M0 0 L520 630 L0 630 Z" fill="${C.green}" fill-opacity="0.06"/>
      <rect x="72" y="110" width="240" height="410" rx="28" fill="${C.dark}" stroke="${C.green}" stroke-opacity="0.45" stroke-width="2"/>
      <circle cx="192" cy="250" r="54" fill="${C.green}" fill-opacity="0.15" stroke="${C.green}" stroke-opacity="0.5"/>
      <rect x="168" y="300" width="48" height="120" rx="24" fill="${C.green}" fill-opacity="0.35"/>
      <rect x="186" y="420" width="12" height="70" rx="6" fill="${C.soft}" fill-opacity="0.35"/>
      <path d="M760 160h280v40H760zM760 230h220v28H760zM760 290h250v28H760z" fill="${C.white}" fill-opacity="0.08"/>
      <circle cx="980" cy="480" r="90" fill="${C.green}" fill-opacity="0.1"/>
      <path d="M900 520 h160 l-28 56 H928 Z" fill="${C.green}" fill-opacity="0.35"/>`;
    },
  },
  tech: {
    label: "TECH · BUSINESS",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${C.black}"/>
          <stop offset="100%" stop-color="${C.dark}"/>
        </linearGradient>
        <pattern id="${id}-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M40 0H0V40" fill="none" stroke="${C.white}" stroke-opacity="0.06"/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <rect width="100%" height="100%" fill="url(#${id}-grid)"/>
      <g stroke="${C.green}" stroke-opacity="0.55" stroke-width="2" fill="none">
        <circle cx="860" cy="180" r="10" fill="${C.green}"/>
        <circle cx="980" cy="260" r="10" fill="${C.green}"/>
        <circle cx="760" cy="300" r="10" fill="${C.green}"/>
        <circle cx="1040" cy="140" r="10" fill="${C.green}"/>
        <circle cx="900" cy="360" r="10" fill="${C.green}"/>
        <path d="M860 180 L980 260 L900 360 L760 300 L860 180 M980 260 L1040 140"/>
      </g>
      <rect x="820" y="420" width="280" height="120" rx="16" fill="${C.gray}" stroke="${C.green}" stroke-opacity="0.35"/>
      <rect x="848" y="448" width="120" height="10" rx="5" fill="${C.green}" fill-opacity="0.7"/>
      <rect x="848" y="474" width="180" height="8" rx="4" fill="${C.white}" fill-opacity="0.15"/>
      <rect x="848" y="498" width="150" height="8" rx="4" fill="${C.white}" fill-opacity="0.1"/>
      <rect x="0" y="0" width="100%" height="6" fill="${C.green}"/>`;
    },
  },
  gospel: {
    label: "GOSPEL · FAITH",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0.5" y1="0" x2="0.5" y2="1">
          <stop offset="0%" stop-color="${C.dark}"/>
          <stop offset="100%" stop-color="${C.black}"/>
        </linearGradient>
        <radialGradient id="${id}-rise" cx="50%" cy="70%" r="55%">
          <stop offset="0%" stop-color="${C.green}" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="${C.green}" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <ellipse cx="600" cy="520" rx="420" ry="200" fill="url(#${id}-rise)"/>
      <g fill="${C.white}" fill-opacity="0.55">
        <circle cx="180" cy="120" r="2"/><circle cx="260" cy="90" r="1.5"/>
        <circle cx="340" cy="140" r="2"/><circle cx="900" cy="100" r="2"/>
        <circle cx="980" cy="160" r="1.5"/><circle cx="1040" cy="80" r="2"/>
        <circle cx="720" cy="70" r="1.5"/><circle cx="480" cy="60" r="2"/>
      </g>
      <path d="M600 140 L618 210 L690 210 L632 252 L654 322 L600 280 L546 322 L568 252 L510 210 L582 210 Z"
        fill="${C.green}" fill-opacity="0.2" stroke="${C.green}" stroke-opacity="0.55" stroke-width="2"/>
      <path d="M120 480 Q600 360 1080 480" fill="none" stroke="${C.green}" stroke-opacity="0.25" stroke-width="3"/>
      <path d="M160 520 Q600 400 1040 520" fill="none" stroke="${C.white}" stroke-opacity="0.08" stroke-width="2"/>`;
    },
  },
  campus: {
    label: "CAMPUS",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${C.black}"/>
          <stop offset="100%" stop-color="${C.gray}"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <g opacity="0.95">
        <rect x="0" y="0" width="100%" height="10" fill="${C.green}"/>
        <rect x="0" y="620" width="100%" height="10" fill="${C.green}" fill-opacity="0.5"/>
        <path d="M0 140 L200 0 H360 L160 140 Z" fill="${C.green}" fill-opacity="0.9"/>
        <path d="M920 0 L1200 0 L1200 200 Z" fill="${C.white}" fill-opacity="0.06"/>
        <path d="M0 440 L400 630 H0 Z" fill="${C.green}" fill-opacity="0.14"/>
        <rect x="0" y="150" width="100%" height="18" fill="${C.green}" fill-opacity="0.12"/>
        <rect x="0" y="178" width="100%" height="8" fill="${C.white}" fill-opacity="0.06"/>
      </g>
      <rect x="860" y="200" width="220" height="220" rx="20" fill="${C.dark}" stroke="${C.green}" stroke-width="3"/>
      <text x="970" y="330" text-anchor="middle" fill="${C.green}" font-family="Manrope,Arial,sans-serif" font-size="72" font-weight="800">26</text>`;
    },
  },
  food: {
    label: "FOOD · LIFESTYLE",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${C.gray}"/>
          <stop offset="100%" stop-color="${C.black}"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <circle cx="900" cy="280" r="200" fill="${C.green}" fill-opacity="0.1"/>
      <circle cx="900" cy="280" r="140" fill="none" stroke="${C.green}" stroke-opacity="0.45" stroke-width="8"/>
      <circle cx="900" cy="280" r="70" fill="${C.green}" fill-opacity="0.18"/>
      <ellipse cx="240" cy="480" rx="180" ry="70" fill="${C.green}" fill-opacity="0.08"/>
      <path d="M120 200c40-80 120-80 160 0s120 80 160 0 120-80 160 0" fill="none" stroke="${C.soft}" stroke-opacity="0.2" stroke-width="4"/>
      <path d="M140 260c36-60 100-60 136 0s100 60 136 0" fill="none" stroke="${C.green}" stroke-opacity="0.35" stroke-width="3"/>
      <rect x="0" y="0" width="10" height="100%" fill="${C.green}"/>`;
    },
  },
  sports: {
    label: "SPORTS",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="${C.black}"/>
          <stop offset="100%" stop-color="${C.dark}"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <g stroke="${C.white}" stroke-opacity="0.12" stroke-width="2" fill="none">
        <rect x="80" y="80" width="1040" height="470" rx="12"/>
        <line x1="600" y1="80" x2="600" y2="550"/>
        <circle cx="600" cy="315" r="70"/>
      </g>
      <path d="M0 180 L420 0 H560 L140 180 Z" fill="${C.green}" fill-opacity="0.85"/>
      <path d="M780 630 L1200 220 V630 Z" fill="${C.green}" fill-opacity="0.12"/>
      <g fill="${C.green}">
        <circle cx="220" cy="400" r="8"/><circle cx="300" cy="360" r="8"/>
        <circle cx="380" cy="420" r="8"/><circle cx="260" cy="480" r="8"/>
      </g>
      <path d="M220 400 L300 360 L380 420 L260 480 Z" fill="none" stroke="${C.green}" stroke-opacity="0.5" stroke-width="2"/>`;
    },
  },
  art: {
    label: "ART · CULTURE",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${C.dark}"/>
          <stop offset="100%" stop-color="${C.black}"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <rect x="700" y="80" width="380" height="280" fill="${C.gray}" stroke="${C.soft}" stroke-opacity="0.2"/>
      <rect x="730" y="110" width="320" height="220" fill="${C.green}" fill-opacity="0.15"/>
      <path d="M760 280 Q860 140 960 260 T1120 200" fill="none" stroke="${C.green}" stroke-width="6" stroke-linecap="round"/>
      <rect x="780" y="400" width="260" height="160" fill="${C.black}" stroke="${C.green}" stroke-opacity="0.4"/>
      <circle cx="910" cy="480" r="36" fill="${C.green}" fill-opacity="0.35"/>
      <path d="M60 520 C200 300 360 560 520 340 S780 200 980 380" fill="none" stroke="${C.white}" stroke-opacity="0.12" stroke-width="10" stroke-linecap="round"/>
      <rect x="64" y="64" width="18" height="18" fill="${C.green}"/>
      <rect x="92" y="64" width="18" height="18" fill="${C.white}" fill-opacity="0.35"/>
      <rect x="120" y="64" width="18" height="18" fill="${C.soft}" fill-opacity="0.2"/>`;
    },
  },
  vault: {
    label: "VAULT",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${C.black}"/>
          <stop offset="60%" stop-color="${C.dark}"/>
          <stop offset="100%" stop-color="${C.gray}"/>
        </linearGradient>
        <linearGradient id="${id}-shine" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="${C.green}" stop-opacity="0"/>
          <stop offset="50%" stop-color="${C.green}" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="${C.green}" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <rect x="720" y="120" width="360" height="390" rx="28" fill="${C.gray}" stroke="${C.green}" stroke-opacity="0.5" stroke-width="2"/>
      <rect x="760" y="160" width="280" height="200" rx="16" fill="${C.black}"/>
      <rect x="760" y="160" width="280" height="200" rx="16" fill="url(#${id}-shine)"/>
      <circle cx="900" cy="420" r="34" fill="none" stroke="${C.green}" stroke-width="4"/>
      <rect x="892" y="420" width="16" height="48" rx="8" fill="${C.green}"/>
      <path d="M80 200 h420" stroke="${C.green}" stroke-opacity="0.3" stroke-width="2"/>
      <path d="M80 240 h300" stroke="${C.white}" stroke-opacity="0.12" stroke-width="2"/>
      <path d="M80 280 h360" stroke="${C.white}" stroke-opacity="0.08" stroke-width="2"/>
      <rect x="0" y="0" width="100%" height="100%" fill="none" stroke="${C.green}" stroke-opacity="0.15" stroke-width="12"/>`;
    },
  },
  memories: {
    label: "MEMORIES",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${C.dark}"/>
          <stop offset="100%" stop-color="${C.black}"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <g transform="rotate(-6 820 280)">
        <rect x="700" y="100" width="300" height="360" fill="${C.white}" fill-opacity="0.92"/>
        <rect x="724" y="124" width="252" height="240" fill="${C.gray}"/>
        <rect x="724" y="124" width="252" height="240" fill="${C.green}" fill-opacity="0.2"/>
        <rect x="744" y="390" width="160" height="12" rx="6" fill="${C.mid}" fill-opacity="0.5"/>
      </g>
      <g transform="rotate(8 980 340)">
        <rect x="860" y="180" width="260" height="320" fill="${C.soft}" fill-opacity="0.2"/>
        <rect x="880" y="200" width="220" height="200" fill="${C.dark}"/>
        <circle cx="990" cy="300" r="40" fill="${C.green}" fill-opacity="0.35"/>
      </g>
      <g fill="${C.green}">
        <rect x="64" y="480" width="28" height="40" rx="2"/>
        <rect x="100" y="480" width="28" height="40" rx="2" fill-opacity="0.55"/>
        <rect x="136" y="480" width="28" height="40" rx="2" fill-opacity="0.3"/>
        <rect x="172" y="480" width="28" height="40" rx="2" fill-opacity="0.15"/>
      </g>`;
    },
  },
  sponsorship: {
    label: "SPONSORSHIP",
    paint(id) {
      return `
      <defs>
        <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="${C.black}"/>
          <stop offset="100%" stop-color="${C.dark}"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#${id}-bg)"/>
      <rect x="0" y="0" width="12" height="100%" fill="${C.green}"/>
      <circle cx="680" cy="200" r="120" fill="${C.green}" fill-opacity="0.12"/>
      <rect x="620" y="140" width="120" height="120" rx="28" fill="${C.green}"/>
      <text x="680" y="218" text-anchor="middle" fill="${C.black}" font-family="Manrope,Arial,sans-serif" font-size="48" font-weight="800">P</text>
      <rect x="560" y="300" width="240" height="8" rx="4" fill="${C.green}" fill-opacity="0.5"/>
      <rect x="590" y="328" width="180" height="6" rx="3" fill="${C.white}" fill-opacity="0.15"/>`;
    },
  },
};

function eventSvg({ seed, category, title, subtitle, gallery = false }) {
  const kit = KITS[category] || KITS.music;
  const id = uid("e", seed);
  const w = 1200;
  const h = 630;
  const titleSize = title.length > 22 ? 48 : title.length > 16 ? 56 : 64;
  const shift = gallery ? 24 : 0;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" fill="none">
  ${kit.paint(id)}
  ${gallery ? `<rect x="40" y="40" width="${w - 80}" height="${h - 80}" fill="none" stroke="${C.white}" stroke-opacity="0.08" stroke-width="2"/>` : ""}
  <text x="${64 + shift}" y="${88 + shift}" fill="${C.green}" font-family="Manrope,Arial,sans-serif" font-size="18" font-weight="700" letter-spacing="3.5">PÀDÉYÁ · ${esc(kit.label)}</text>
  <text x="${64 + shift}" y="${280 + (gallery ? 20 : 0)}" fill="${C.white}" font-family="Manrope,Arial,sans-serif" font-size="${titleSize}" font-weight="800">${esc(title)}</text>
  <text x="${64 + shift}" y="${340 + (gallery ? 20 : 0)}" fill="${C.soft}" font-family="Manrope,Arial,sans-serif" font-size="26">${esc(subtitle)}</text>
  <rect x="${64 + shift}" y="${378 + (gallery ? 20 : 0)}" width="160" height="6" rx="3" fill="${C.green}"/>
</svg>
`;
}

function hostCoverSvg({ seed, category, name, role }) {
  const kit = KITS[category] || KITS.music;
  const id = uid("hc", seed);
  // Scale 1200×630 kits into 1200×480 cover frames
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="480" viewBox="0 0 1200 480" fill="none">
  <g transform="translate(0,-40) scale(1,0.84)">
    ${kit.paint(id)}
  </g>
  <rect x="0" y="300" width="1200" height="180" fill="${C.black}" fill-opacity="0.58"/>
  <text x="64" y="72" fill="${C.green}" font-family="Manrope,Arial,sans-serif" font-size="16" font-weight="700" letter-spacing="3.5">PÀDÉYÁ · HOST · ${esc(kit.label)}</text>
  <text x="64" y="380" fill="${C.white}" font-family="Manrope,Arial,sans-serif" font-size="48" font-weight="800">${esc(name)}</text>
  <text x="64" y="428" fill="${C.soft}" font-family="Manrope,Arial,sans-serif" font-size="22">${esc(role)}</text>
</svg>
`;
}

function hostAvatarSvg({ seed, category, initials, label }) {
  const id = uid("ha", seed);
  const motifs = {
    music: `<circle cx="360" cy="140" r="120" fill="${C.green}" fill-opacity="0.2"/>
      <path d="M60 360 C140 260 220 420 300 320 S420 240 480 340" fill="none" stroke="${C.green}" stroke-width="8"/>`,
    comedy: `<ellipse cx="160" cy="0" rx="160" ry="220" fill="${C.white}" fill-opacity="0.12"/>
      <rect x="340" y="300" width="120" height="160" rx="16" fill="${C.green}" fill-opacity="0.25"/>`,
    tech: `<g stroke="${C.green}" stroke-opacity="0.6" fill="${C.green}">
        <circle cx="120" cy="120" r="8"/><circle cx="400" cy="160" r="8"/>
        <circle cx="360" cy="380" r="8"/><circle cx="140" cy="400" r="8"/>
        <path d="M120 120 L400 160 L360 380 L140 400 Z" fill="none" stroke-width="3"/>
      </g>`,
    gospel: `<ellipse cx="256" cy="420" rx="180" ry="90" fill="${C.green}" fill-opacity="0.2"/>
      <path d="M256 90 L268 150 L330 150 L280 188 L298 248 L256 212 L214 248 L232 188 L182 150 L244 150 Z" fill="${C.green}" fill-opacity="0.35"/>`,
  };
  const motif = motifs[category] || motifs.music;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512" fill="none">
  <defs>
    <linearGradient id="${id}-bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${C.black}"/>
      <stop offset="100%" stop-color="${C.dark}"/>
    </linearGradient>
    <clipPath id="${id}-clip"><circle cx="256" cy="256" r="256"/></clipPath>
  </defs>
  <g clip-path="url(#${id}-clip)">
    <rect width="512" height="512" fill="url(#${id}-bg)"/>
    ${motif}
    <circle cx="256" cy="256" r="118" fill="${C.black}" fill-opacity="0.55" stroke="${C.green}" stroke-width="4"/>
    <text x="256" y="282" text-anchor="middle" fill="${C.white}" font-family="Manrope,Arial,sans-serif" font-size="72" font-weight="800">${esc(initials)}</text>
  </g>
  <circle cx="256" cy="256" r="250" fill="none" stroke="${C.green}" stroke-opacity="0.45" stroke-width="6"/>
  <title>${esc(label)}</title>
</svg>
`;
}

function vaultSvg({ seed, category, title, subtitle }) {
  const kit = KITS.vault;
  const accent = KITS[category] || KITS.vault;
  const id = uid("v", seed);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" fill="none">
  ${kit.paint(id)}
  <text x="64" y="96" fill="${C.green}" font-family="Manrope,Arial,sans-serif" font-size="18" font-weight="700" letter-spacing="3.5">PÀDÉYÁ · ${esc(accent.label)} · VAULT</text>
  <text x="64" y="280" fill="${C.white}" font-family="Manrope,Arial,sans-serif" font-size="54" font-weight="800">${esc(title)}</text>
  <text x="64" y="340" fill="${C.soft}" font-family="Manrope,Arial,sans-serif" font-size="24">${esc(subtitle)}</text>
  <rect x="64" y="378" width="140" height="6" rx="3" fill="${C.green}"/>
</svg>
`;
}

function memorySvg({ seed, category, title, subtitle }) {
  const kit = KITS.memories;
  const id = uid("m", seed);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" fill="none">
  ${kit.paint(id)}
  <text x="64" y="96" fill="${C.green}" font-family="Manrope,Arial,sans-serif" font-size="18" font-weight="700" letter-spacing="3.5">PÀDÉYÁ · ${(KITS[category] || KITS.memories).label} · MEMORY</text>
  <text x="64" y="300" fill="${C.white}" font-family="Manrope,Arial,sans-serif" font-size="48" font-weight="800">${esc(title)}</text>
  <text x="64" y="358" fill="${C.soft}" font-family="Manrope,Arial,sans-serif" font-size="24">${esc(subtitle)}</text>
  <rect x="64" y="396" width="140" height="6" rx="3" fill="${C.green}"/>
</svg>
`;
}

function sponsorSvg({ seed, name, tagline, mark }) {
  const id = uid("s", seed);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400" fill="none">
  ${KITS.sponsorship.paint(id)}
  <text x="64" y="88" fill="${C.green}" font-family="Manrope,Arial,sans-serif" font-size="14" font-weight="700" letter-spacing="3">PÀDÉYÁ · SPONSOR</text>
  <text x="64" y="220" fill="${C.white}" font-family="Manrope,Arial,sans-serif" font-size="48" font-weight="800">${esc(name)}</text>
  <text x="64" y="270" fill="${C.soft}" font-family="Manrope,Arial,sans-serif" font-size="20">${esc(tagline)}</text>
  <rect x="620" y="140" width="120" height="120" rx="28" fill="${C.green}"/>
  <text x="680" y="218" text-anchor="middle" fill="${C.black}" font-family="Manrope,Arial,sans-serif" font-size="42" font-weight="800">${esc(mark)}</text>
</svg>
`;
}

function write(rel, content) {
  const path = join(ROOT, rel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
  console.log("wrote", rel);
}

const EVENTS = [
  ["afrobeats-night-live", "music", "Afrobeats Night Live", "Lagos · Sound · Movement"],
  ["detty-friday-live", "music", "Detty Friday Live", "Island energy. Verified door."],
  ["mainland-vibes-summer", "music", "Mainland Vibes Summer", "Open air. Peak season."],
  ["mainland-vibes-2025", "music", "Mainland Vibes 2025", "The night that defined the year"],
  ["pending-neon-nights", "music", "Neon Nights", "Pending review · Nightlife"],
  ["cancelled-beach-bash", "music", "Beach Bash", "Coastal night · Cancelled demo"],
  ["draft-secret-session", "music", "Secret Session", "Invite-only draft event"],
  ["rejected-stadium-show", "music", "Stadium Show", "Rejected listing · Demo"],
  ["lagos-comedy-jam", "comedy", "Lagos Comedy Jam", "Island laughs. Verified nights."],
  ["island-comedy-night", "comedy", "Island Comedy Night", "Mic check. Crowd on."],
  ["founders-mixer-lagos", "tech", "Founders Mixer Lagos", "Builders · Brands · Capital"],
  ["product-builders-meetup", "tech", "Product Builders Meetup", "Ship faster with community"],
  ["startup-demo-evening", "tech", "Startup Demo Evening", "Pitch. Feedback. Connect."],
  ["worship-under-stars", "gospel", "Worship Under Stars", "Open-air praise night"],
  ["praise-experience-live", "gospel", "Praise Experience Live", "Faith · Sound · Presence"],
  ["campus-fest-2026", "campus", "Campus Fest 2026", "Students. Stage. Season."],
  ["food-and-flow", "food", "Food & Flow", "Taste · Playlist · People"],
  ["rooftop-games-night", "sports", "Rooftop Games Night", "Casual sports · City views"],
  ["sports-sunday", "sports", "Sports Sunday", "Watch party · Community turf"],
  ["art-walk-lagos", "art", "Art Walk Lagos", "Galleries · Streets · Culture"],
];

const HOSTS = [
  ["djmaze", "music", "DJ Maze", "Music / Nightlife", "DM"],
  ["lagoscomedyhub", "comedy", "Lagos Comedy Hub", "Comedy collective", "LC"],
  ["mainlandvibes", "music", "Mainland Vibes", "Lifestyle nightlife", "MV"],
  ["techconnectafrica", "tech", "TechConnect Africa", "Tech & business", "TC"],
  ["praiseexperience", "gospel", "Praise Experience", "Gospel nights", "PE"],
];

const VAULT = [
  ["vip-gallery", "vault", "VIP Photo Gallery", "Exclusive drop · Ticket holders"],
  ["unreleased-set", "music", "Unreleased Set", "Audio vault · Members only"],
  ["bts-mainland", "memories", "BTS Mainland", "Behind the scenes reel"],
  ["worship-rehearsal", "gospel", "Worship Rehearsal", "Private rehearsal footage"],
  ["founder-deck", "tech", "Founder Deck", "Slide vault · Paid unlock"],
  ["comedy-early", "comedy", "Comedy Early Cuts", "Unreleased punch-ups"],
];

const MEMORIES = [
  ["mainland-2025-memory", "music", "Mainland 2025", "Night archived forever"],
  ["detty-friday-memory", "music", "Detty Friday Memory", "Crowd · Lights · Replay"],
  ["island-comedy-memory", "comedy", "Island Comedy Memory", "The set that sold out"],
];

const SPONSORS = [
  ["acme-events", "Acme Events", "Title packages for nights that convert", "AE"],
  ["greenline-media", "Greenline Media", "Brand stories for live culture", "GL"],
  ["nova-sips", "Nova Sips", "Beverage partner for peak nights", "NS"],
];

for (const [slug, category, title, subtitle] of EVENTS) {
  write(
    `events/${slug}.svg`,
    eventSvg({ seed: slug, category, title, subtitle }),
  );
  write(
    `events/${slug}-gallery.svg`,
    eventSvg({
      seed: `${slug}-g`,
      category,
      title,
      subtitle: gallerySubtitle(category, subtitle),
      gallery: true,
    }),
  );
}

function gallerySubtitle(category, base) {
  const extras = {
    music: "Gallery cut · Stage lights",
    comedy: "Gallery cut · Mic energy",
    tech: "Gallery cut · Room moments",
    gospel: "Gallery cut · Worship frames",
    campus: "Gallery cut · Campus energy",
    food: "Gallery cut · Table scenes",
    sports: "Gallery cut · Game day",
    art: "Gallery cut · Exhibit walk",
  };
  return extras[category] || base;
}

for (const [slug, category, name, role, initials] of HOSTS) {
  write(
    `hosts/${slug}-cover.svg`,
    hostCoverSvg({ seed: slug, category, name, role }),
  );
  write(
    `hosts/${slug}-avatar.svg`,
    hostAvatarSvg({ seed: `${slug}-a`, category, initials, label: name }),
  );
}

for (const [slug, category, title, subtitle] of VAULT) {
  write(`vault/${slug}.svg`, vaultSvg({ seed: slug, category, title, subtitle }));
}

for (const [slug, category, title, subtitle] of MEMORIES) {
  write(
    `memories/${slug}.svg`,
    memorySvg({ seed: slug, category, title, subtitle }),
  );
}

for (const [slug, name, tagline, mark] of SPONSORS) {
  write(`sponsors/${slug}.svg`, sponsorSvg({ seed: slug, name, tagline, mark }));
}

console.log("\nDemo assets regenerated.");
