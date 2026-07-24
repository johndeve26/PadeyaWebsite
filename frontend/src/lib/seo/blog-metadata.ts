import type { Metadata } from "next";

import type { BlogPost } from "@/lib/blog-api";
import { brand } from "@/lib/brand";
import { absoluteUrl, buildPageMetadata, defaultOgImage } from "@/lib/seo/site";

export function blogPostMetadata(post: BlogPost): Metadata {
  const title = post.seo_title || post.title;
  const description =
    post.seo_description ||
    post.excerpt ||
    `Read ${post.title} on the Pàdéyá blog.`;
  const image = post.og_image_url || post.cover_url || defaultOgImage();
  const canonical = post.canonical_url || absoluteUrl(`/blog/${post.slug}`);
  const meta = buildPageMetadata({
    title,
    description,
    path: `/blog/${post.slug}`,
    image,
  });
  return {
    ...meta,
    alternates: { canonical },
    robots:
      post.status === "published"
        ? { index: true, follow: true }
        : { index: false, follow: false },
  };
}

export function blogIndexMetadata(): Metadata {
  return buildPageMetadata({
    title: "Blog",
    description: `Blog posts and editorial from ${brand.name} — event discovery, host growth, ticketing safety, Fan Passport, Ambassadors, and platform updates.`,
    path: "/blog",
  });
}

export function articleJsonLd(post: BlogPost, origin: string) {
  const url = `${origin.replace(/\/$/, "")}/blog/${post.slug}`;
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.seo_description || post.excerpt || post.title,
    image: post.og_image_url || post.cover_url || undefined,
    datePublished: post.published_at || undefined,
    dateModified: post.updated_at || post.published_at || undefined,
    author: post.author
      ? {
          "@type": "Person",
          name: post.author.display_name,
          url: `${origin}/blog/author/${post.author.slug}`,
        }
      : { "@type": "Organization", name: brand.name },
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
