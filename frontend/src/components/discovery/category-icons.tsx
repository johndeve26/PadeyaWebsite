import { cn } from "@/lib/cn";

/** Compact category glyphs — inline SVG, no icon dependency. */
export function CategoryGlyph({
  slug,
  className = "",
}: {
  slug: string;
  className?: string;
}) {
  const common = cn("h-5 w-5", className);
  switch (slug) {
    case "music":
    case "nightlife":
      return (
        <svg viewBox="0 0 24 24" fill="none" className={common} aria-hidden>
          <path
            d="M9 18V6l10-2v12"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="7" cy="18" r="2.5" fill="currentColor" />
          <circle cx="17" cy="16" r="2.5" fill="currentColor" />
        </svg>
      );
    case "comedy":
      return (
        <svg viewBox="0 0 24 24" fill="none" className={common} aria-hidden>
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
          <path
            d="M8.5 14.5c1.2 1.4 2.6 2 3.5 2s2.3-.6 3.5-2"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <circle cx="9" cy="10" r="1.2" fill="currentColor" />
          <circle cx="15" cy="10" r="1.2" fill="currentColor" />
        </svg>
      );
    case "tech":
    case "business":
      return (
        <svg viewBox="0 0 24 24" fill="none" className={common} aria-hidden>
          <rect
            x="3"
            y="5"
            width="18"
            height="12"
            rx="2"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M8 21h8M12 17v4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      );
    case "food-drink":
      return (
        <svg viewBox="0 0 24 24" fill="none" className={common} aria-hidden>
          <path
            d="M8 3v8M6 3v4a2 2 0 0 0 4 0V3M16 3v18M14 3c0 3 4 3 4 6"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "arts-culture":
    case "art-culture":
    case "lifestyle":
      return (
        <svg viewBox="0 0 24 24" fill="none" className={common} aria-hidden>
          <path
            d="M4 19l5-14 4 10 2-6 5 10"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "gospel":
    case "community":
    case "campus":
      return (
        <svg viewBox="0 0 24 24" fill="none" className={common} aria-hidden>
          <path
            d="M12 3v18M5 8h14M8 21h8"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 24 24" fill="none" className={common} aria-hidden>
          <path
            d="M12 4l2.2 4.5 5 .7-3.6 3.5.9 5L12 15.4 7.5 17.7l.9-5L4.8 9.2l5-.7L12 4z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        </svg>
      );
  }
}
