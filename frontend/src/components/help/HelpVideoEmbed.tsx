/** Safe video embed — YouTube/Vimeo iframe only when embed_url is present. */

export function HelpVideoEmbed({
  embedUrl,
  title,
  provider,
  externalUrl,
}: {
  embedUrl?: string | null;
  title: string;
  provider?: string | null;
  externalUrl?: string | null;
}) {
  if (embedUrl) {
    return (
      <div className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink shadow-[var(--shadow)]">
        <div className="relative aspect-video w-full">
          <iframe
            src={embedUrl}
            title={title}
            className="absolute inset-0 h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
          />
        </div>
      </div>
    );
  }

  if (externalUrl && provider === "external") {
    return (
      <p className="rounded-[var(--radius-lg)] border border-border bg-surface-muted px-5 py-4 text-sm text-foreground">
        Watch on{" "}
        <a
          href={externalUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-primary-text underline-offset-4 hover:underline"
        >
          external video
        </a>
        . Unsafe embeds are never injected.
      </p>
    );
  }

  return null;
}
