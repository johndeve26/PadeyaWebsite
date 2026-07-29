import Link from "next/link";

import { BlogCard } from "@/components/blog/BlogCard";
import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { Button, Container, EmptyState, SectionHeader } from "@/components/ui";
import { fetchBlogPostsServer } from "@/lib/blog-api";

export async function HomeBlogTeaser() {
  const posts = await fetchBlogPostsServer({ limit: 3 });

  return (
    <section className="bg-background py-10 sm:py-12">
      <Container className="space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <SectionHeader
            variant="display"
            eyebrow="Blog"
            title="Stories for hosts and fans"
            description="Event planning tips, host growth, ticketing safety, and platform updates from the Pàdéyá blog."
          />
          <Link href="/blog" className="shrink-0">
            <Button variant="primary" size="lg">
              Read the blog
            </Button>
          </Link>
        </div>
        {posts.length ? (
          <HomeCardCarousel
            label="Blog stories"
            until="lg"
            desktopGridClassName="lg:grid-cols-3"
            slideClassName="w-[min(82vw,19.5rem)] sm:w-[min(46vw,21rem)]"
          >
            {posts.map((post, i) => (
              <BlogCard
                key={post.id}
                post={post}
                listContext="homepage_blog"
                cardPosition={i}
              />
            ))}
          </HomeCardCarousel>
        ) : (
          <EmptyState
            title="Blog posts are on the way"
            description="Meanwhile, explore events or open Support if you need help tonight."
            action={
              <Link
                href="/events"
                className="text-sm font-semibold text-primary-text"
              >
                Explore events
              </Link>
            }
          />
        )}
      </Container>
    </section>
  );
}
