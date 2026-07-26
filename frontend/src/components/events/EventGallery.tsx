"use client";

import { useState } from "react";

import { Button, Media, Modal } from "@/components/ui";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import type { EventItem, EventMedia } from "@/lib/types/events";

import { EventDetailPanel } from "./EventDetailPanel";

/** Click-to-load facade — avoids shipping YouTube player JS until interaction. */
function LazyVideoEmbed({
  title,
  src,
}: {
  title: string;
  src: string;
}) {
  const [active, setActive] = useState(false);
  if (!active) {
    return (
      <button
        type="button"
        onClick={() => setActive(true)}
        className="flex aspect-video w-full items-center justify-center bg-ink text-sm font-semibold text-paper transition-colors hover:bg-ink/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        aria-label={`Play ${title}`}
      >
        Play teaser
      </button>
    );
  }
  return (
    <iframe
      title={title}
      src={src}
      className="aspect-video w-full"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowFullScreen
      referrerPolicy="strict-origin-when-cross-origin"
    />
  );
}

function galleryItems(event: EventItem): EventMedia[] {
  const fromMedia = [...(event.media ?? [])]
    .filter((m) => m.media_type === "gallery" && m.url?.trim())
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  if (fromMedia.length) return fromMedia;
  return [];
}

function youtubeEmbed(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtu.be")) {
      const id = u.pathname.replace("/", "").trim();
      return id ? `https://www.youtube.com/embed/${id}` : null;
    }
    if (u.hostname.includes("youtube.com")) {
      const id = u.searchParams.get("v");
      return id ? `https://www.youtube.com/embed/${id}` : null;
    }
  } catch {
    return null;
  }
  return null;
}

function vimeoEmbed(url: string): string | null {
  try {
    const u = new URL(url);
    if (!u.hostname.includes("vimeo.com")) return null;
    const id = u.pathname.split("/").filter(Boolean).pop();
    return id ? `https://player.vimeo.com/video/${id}` : null;
  } catch {
    return null;
  }
}

/** Gallery images, teaser video, and sponsor logos for the public event page. */
export function EventGallery({ event }: { event: EventItem }) {
  const gallery = galleryItems(event);
  const teaser = event.teaser_video_url?.trim() || null;
  const sponsors = (event.sponsor_logo_urls ?? []).filter((u) => u?.trim());
  const embed = teaser
    ? youtubeEmbed(teaser) || vimeoEmbed(teaser)
    : null;
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  if (!gallery.length && !teaser && !sponsors.length) return null;

  const active =
    activeIndex != null && gallery[activeIndex] ? gallery[activeIndex] : null;

  function openAt(index: number) {
    setActiveIndex(index);
    track(TrackedAction.EVENT_GALLERY_VIEW, {
      targetEventId: event.id,
      hostId: event.host_id,
      immediate: true,
      metadata: {
        media_id: gallery[index]?.id,
        card_position: index,
      },
    });
  }

  function closeLightbox() {
    setActiveIndex(null);
  }

  function showPrev() {
    if (activeIndex == null || gallery.length < 2) return;
    setActiveIndex((activeIndex - 1 + gallery.length) % gallery.length);
  }

  function showNext() {
    if (activeIndex == null || gallery.length < 2) return;
    setActiveIndex((activeIndex + 1) % gallery.length);
  }

  return (
    <EventDetailPanel title="Gallery & media">
      <div className="space-y-6">
        {gallery.length ? (
          <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3">
            {gallery.map((item, index) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => openAt(index)}
                  className="group relative aspect-[4/3] w-full overflow-hidden rounded-[var(--radius-md)] border border-border bg-surface-dark text-left transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-[var(--shadow)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  aria-label={
                    item.alt_text?.trim()
                      ? `View ${item.alt_text}`
                      : `View gallery image ${index + 1}`
                  }
                >
                  <Media
                    src={item.url}
                    alt={item.alt_text || ""}
                    className="object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                    sizes="(max-width: 640px) 50vw, 33vw"
                  />
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        {teaser ? (
          <div className="space-y-2">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
              Teaser
            </p>
            {embed ? (
              <div className="overflow-hidden rounded-[var(--radius-md)] border border-border bg-surface-dark">
                <LazyVideoEmbed title="Event teaser video" src={embed} />
              </div>
            ) : (
              <a
                href={teaser}
                target="_blank"
                rel="noreferrer"
                className="text-sm font-semibold text-foreground underline decoration-accent underline-offset-2"
              >
                Watch teaser
              </a>
            )}
          </div>
        ) : null}

        {sponsors.length ? (
          <div className="space-y-2">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
              Sponsors
            </p>
            <ul className="flex flex-wrap items-center gap-3">
              {sponsors.map((url) => (
                <li
                  key={url}
                  className="relative h-12 w-24 overflow-hidden rounded-[var(--radius-sm)] border border-border bg-card p-1.5"
                >
                  <Media src={url} alt="" className="object-contain" />
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <Modal
        open={active != null}
        onClose={closeLightbox}
        title={
          active?.alt_text?.trim() ||
          (activeIndex != null
            ? `Gallery ${activeIndex + 1} of ${gallery.length}`
            : "Gallery")
        }
        description={
          gallery.length > 1 && activeIndex != null
            ? `${activeIndex + 1} of ${gallery.length}`
            : undefined
        }
        className="sm:max-w-3xl"
        footer={
          gallery.length > 1 ? (
            <>
              <Button variant="secondary" onClick={showPrev}>
                Previous
              </Button>
              <Button onClick={showNext}>Next</Button>
            </>
          ) : undefined
        }
      >
        {active?.url ? (
          <div className="relative aspect-[4/3] overflow-hidden rounded-[var(--radius-md)] bg-surface-dark sm:aspect-[16/10]">
            <Media
              src={active.url}
              alt={active.alt_text || ""}
              className="object-contain"
            />
          </div>
        ) : null}
      </Modal>
    </EventDetailPanel>
  );
}
