import { buildPageMetadata } from "./site";

export { buildHostMetadata } from "./host-metadata";

export function buildHubMetadata(opts: {
  title: string;
  description: string;
  path: string;
}) {
  return buildPageMetadata(opts);
}
