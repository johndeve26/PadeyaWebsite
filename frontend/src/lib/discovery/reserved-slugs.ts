/**
 * Path segments under `/events/*` that must not collide with event slugs.
 * Keep in sync with discovery hubs in docs/TAXONOMY_AND_CONTENT_GRAPH.md.
 */
export const RESERVED_EVENT_PATH_SLUGS = new Set([
  "c",
  "city",
  "tag",
  "vibe",
  "free",
  "vip",
  "this-weekend",
  "near-me",
  "hosts",
]);
