import type { Metadata } from "next";

import type { HelpArticle } from "@/lib/knowledge-base/api";
import { brand } from "@/lib/brand";
import { absoluteUrl, buildPageMetadata, defaultOgImage } from "@/lib/seo/site";

export function helpIndexMetadata(): Metadata {
  return buildPageMetadata({
    title: "Help Center",
    description: `Guides for fans, hosts, and admins on ${brand.name} — tickets, events, Fan Passport, check-in, account safety, and more.`,
    path: "/help",
  });
}

export function helpCategoryMetadata(
  name: string,
  slug: string,
  description?: string | null,
): Metadata {
  return buildPageMetadata({
    title: `${name} · Help`,
    description:
      description ||
      `${name} guides on the ${brand.name} Help Center.`,
    path: `/help/${slug}`,
  });
}

export function helpArticleMetadata(article: HelpArticle): Metadata {
  const title = article.seo_title || article.title;
  const description =
    article.seo_description ||
    article.excerpt ||
    `${article.title} — ${brand.name} Help Center.`;
  const image =
    article.video_thumbnail_url || article.cover_url || defaultOgImage();
  const canonical = absoluteUrl(`/help/articles/${article.slug}`);
  const meta = buildPageMetadata({
    title,
    description,
    path: `/help/articles/${article.slug}`,
    image,
  });
  return {
    ...meta,
    alternates: { canonical },
    robots:
      article.status === "published"
        ? { index: true, follow: true }
        : { index: false, follow: false },
  };
}

export function helpArticleJsonLd(article: HelpArticle, origin: string) {
  const url = `${origin.replace(/\/$/, "")}/help/articles/${article.slug}`;
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.seo_description || article.excerpt || article.title,
    image:
      article.video_thumbnail_url || article.cover_url || undefined,
    datePublished: article.published_at || undefined,
    dateModified: article.updated_at || article.published_at || undefined,
    author: { "@type": "Organization", name: brand.name },
    publisher: {
      "@type": "Organization",
      name: brand.name,
      logo: {
        "@type": "ImageObject",
        url: `${origin}${brand.logos.light}`,
      },
    },
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    url,
  };
}
