import { buildPageMetadata } from "./site";

export function buildHubMetadata(opts: {
  title: string;
  description: string;
  path: string;
}) {
  return buildPageMetadata(opts);
}

export function buildHostMetadata(opts: {
  displayName: string;
  bio?: string | null;
  slug: string;
  image?: string | null;
}) {
  return buildPageMetadata({
    title: opts.displayName,
    description:
      opts.bio?.slice(0, 160) ||
      `${opts.displayName} on Pàdéyá — upcoming events, Memories, and Vault.`,
    path: `/@${opts.slug}`,
    image: opts.image,
  });
}
