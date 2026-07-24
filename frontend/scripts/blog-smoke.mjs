/**
 * Blog platform smoke checks — routes, SEO, CMS, sitemap wiring.
 * Run: npm run test:blog
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

const required = [
  "src/app/blog/page.tsx",
  "src/app/blog/[slug]/page.tsx",
  "src/app/blog/category/[slug]/page.tsx",
  "src/app/blog/tag/[slug]/page.tsx",
  "src/app/blog/author/[slug]/page.tsx",
  "src/app/admin/blog/page.tsx",
  "src/app/admin/blog/new/page.tsx",
  "src/app/admin/blog/[postId]/edit/page.tsx",
  "src/app/admin/blog/categories/page.tsx",
  "src/app/admin/blog/tags/page.tsx",
  "src/components/blog/BlogCard.tsx",
  "src/components/blog/BlogFilterBar.tsx",
  "src/components/blog/BlogShare.tsx",
  "src/components/blog/BlogToc.tsx",
  "src/components/blog/BlogArticleBody.tsx",
  "src/components/blog/BlogRecoveryCtas.tsx",
  "src/lib/blog-api.ts",
  "src/lib/seo/blog-metadata.ts",
];

for (const rel of required) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const index = read("src/app/blog/page.tsx");
assert.match(index, /fetchBlogPostsServer/);
assert.match(index, /BlogFilterBar/);
assert.match(index, /BlogCard/);

const detail = read("src/app/blog/[slug]/page.tsx");
assert.match(detail, /notFound\(\)/);
assert.match(detail, /articleJsonLd/);
assert.match(detail, /blogPostMetadata/);
assert.match(detail, /status !== "published"/);

const meta = read("src/lib/seo/blog-metadata.ts");
assert.match(meta, /robots/);
assert.match(meta, /@type": "Article"/);
assert.match(meta, /canonical/);

const sitemap = read("src/app/sitemap.ts");
assert.match(sitemap, /fetchBlogPostsServer/);
assert.match(sitemap, /\/blog/);
assert.match(sitemap, /status !== "published"/);

const nav = read("src/lib/nav/workspace.ts");
assert.match(nav, /href: "\/admin\/blog"/);
assert.match(nav, /admin\.blog\.view/);

const header = read("src/components/layout/headerNav.ts");
assert.match(header, /href: "\/blog"/);
assert.match(
  read("src/components/layout/HeaderResourcesDropdown.tsx"),
  /ResourcesMegaPanel/,
);
assert.match(
  read("src/components/layout/ResourcesMegaPanel.tsx"),
  /RESOURCES_LEARN/,
);

const footer = read("src/components/layout/SiteFooter.tsx");
assert.match(footer, /href: "\/blog"/);

const api = read("src/lib/blog-api.ts");
assert.match(api, /\/admin\/blog\/posts/);
assert.match(api, /publishAdminBlogPost/);
assert.match(api, /fetchBlogPostServer/);
assert.match(api, /body_html/);

const edit = read("src/app/admin/blog/[postId]/edit/page.tsx");
assert.match(edit, /admin_notes/);
assert.match(edit, /Publish now/);
assert.match(edit, /Unpublish/);

const cmsRedirect = read("src/app/admin/cms/blog/page.tsx");
assert.match(cmsRedirect, /redirect\("\/admin\/blog"\)/);

console.log("blog-smoke: ok");
