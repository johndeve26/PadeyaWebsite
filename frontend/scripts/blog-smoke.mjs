/**
 * Blog platform smoke checks — routes, SEO, CMS, sitemap, Blog AI Studio.
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
  "src/components/blog/BlogAIAssist.tsx",
  "src/lib/blog-api.ts",
  "src/lib/blog-studio-api.ts",
  "src/lib/seo/blog-metadata.ts",
  "src/components/blog/studio/types.ts",
  "src/components/blog/studio/BlogStudioShell.tsx",
  "src/components/blog/studio/BlogContentBriefPanel.tsx",
  "src/components/blog/studio/BlogAiWorkflow.tsx",
  "src/components/blog/studio/BlogOutlineEditor.tsx",
  "src/components/blog/studio/BlogSectionToolbar.tsx",
  "src/components/blog/studio/BlogSeoPanel.tsx",
  "src/components/blog/studio/BlogImageAssistant.tsx",
  "src/components/blog/studio/BlogQualityReviewPanel.tsx",
  "src/components/blog/studio/BlogFactReviewPanel.tsx",
  "src/components/blog/studio/BlogInternalLinksPanel.tsx",
  "src/components/blog/studio/BlogFaqEditor.tsx",
  "src/components/blog/studio/BlogVersionHistory.tsx",
  "src/components/blog/studio/BlogPublishPanel.tsx",
  "src/components/blog/studio/AiGenerationProgress.tsx",
  "src/components/blog/studio/AiSuggestionDiff.tsx",
  "src/components/blog/studio/BlogInlineAiMenu.tsx",
  "src/components/blog/studio/useBlogStudioAutosave.ts",
  "src/components/blog/studio/BlogStudioProvider.tsx",
  "src/components/blog/studio/BlogStudioPage.tsx",
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

const studioApi = read("src/lib/blog-studio-api.ts");
assert.match(studioApi, /\/admin\/blog\/ai\//);
assert.match(studioApi, /seo-brief/);
assert.match(studioApi, /full-draft/);
assert.match(studioApi, /rewrite/);
assert.match(studioApi, /autosave/);
assert.match(studioApi, /\/admin\/blog\/preview\//);

const newPage = read("src/app/admin/blog/new/page.tsx");
assert.match(newPage, /BlogStudioPage/);
assert.match(newPage, /mode="new"/);

const edit = read("src/app/admin/blog/[postId]/edit/page.tsx");
assert.match(edit, /BlogStudioPage/);
assert.match(edit, /mode="edit"/);

const publishPanel = read(
  "src/components/blog/studio/BlogPublishPanel.tsx",
);
assert.match(publishPanel, /Admin notes/);
assert.match(publishPanel, /Publish/);
assert.match(publishPanel, /Unpublish/);
assert.match(publishPanel, /AI never auto-publishes/);
assert.match(publishPanel, /ConfirmAction/);

const assist = read("src/components/blog/BlogAIAssist.tsx");
assert.match(assist, /export function BlogAIAssist/);

const types = read("src/components/blog/studio/types.ts");
assert.match(types, /How-to guide/);
assert.match(types, /Informational/);
assert.match(types, /Professional/);
assert.match(types, /padeya|Pàdéyá|BlogContentBrief/i);

const autosave = read("src/components/blog/studio/useBlogStudioAutosave.ts");
assert.match(autosave, /padeya-blog-studio-draft/);
assert.match(autosave, /autosaveStatus: "saving"/);
assert.match(autosave, /beforeunload/);

const settings = read("src/components/blog/studio/BlogSettingsSummary.tsx");
assert.match(settings, /Saving…/);
assert.match(settings, /Saved/);
assert.match(settings, /Save failed/);

const suggestion = read("src/components/blog/studio/AiSuggestionDiff.tsx");
assert.match(suggestion, /Insert below/);
assert.match(suggestion, /Replace/);
assert.match(suggestion, /Discard/);
assert.match(suggestion, /Apply/);

const image = read("src/components/blog/studio/BlogImageAssistant.tsx");
assert.match(image, /SVG/);
assert.match(image, /does not auto-upload/);

const cmsRedirect = read("src/app/admin/cms/blog/page.tsx");
assert.match(cmsRedirect, /redirect\("\/admin\/blog"\)/);

// No Playwright admin-blog critical path in this repo yet — studio is covered by
// smoke file/string assertions + backend tests. Add e2e only when a Playwright
// suite for admin blog already exists.
console.log("blog-smoke: ok");
console.log(
  "blog-smoke note: Playwright admin-blog critical path not present; remaining limitation documented.",
);
