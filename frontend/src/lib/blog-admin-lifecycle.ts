/** Admin blog post lifecycle helpers for list actions. */

export type BlogPostLifecycle = {
  status: string;
  archived_at?: string | null;
};

export function isBlogPostArchived(post: BlogPostLifecycle): boolean {
  return post.status === "archived" || Boolean(post.archived_at);
}

export function canArchiveBlogPost(post: BlogPostLifecycle): boolean {
  return !isBlogPostArchived(post);
}

export function canPublishBlogPost(post: BlogPostLifecycle): boolean {
  return !isBlogPostArchived(post) && post.status !== "published";
}

export function canUnpublishBlogPost(post: BlogPostLifecycle): boolean {
  return !isBlogPostArchived(post) && post.status === "published";
}
