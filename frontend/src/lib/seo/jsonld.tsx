import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";

export function breadcrumbJsonLd(
  items: BreadcrumbItem[],
  origin: string,
): Record<string, unknown> {
  const elements = items.map((item, index) => {
    const entry: Record<string, unknown> = {
      "@type": "ListItem",
      position: index + 1,
      name: item.label,
    };
    if (item.href) {
      entry.item = item.href.startsWith("http")
        ? item.href
        : `${origin.replace(/\/$/, "")}${item.href}`;
    }
    return entry;
  });

  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: elements,
  };
}

/** CollectionPage for discovery hub landing pages. */
export function collectionPageJsonLd(opts: {
  name: string;
  description: string;
  path: string;
  origin: string;
}): Record<string, unknown> {
  const url = opts.path.startsWith("http")
    ? opts.path
    : `${opts.origin.replace(/\/$/, "")}${opts.path}`;
  return {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: opts.name,
    description: opts.description,
    url,
    isPartOf: {
      "@type": "WebSite",
      name: "Pàdéyá",
      url: opts.origin.replace(/\/$/, ""),
    },
  };
}

export function JsonLdScript({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
