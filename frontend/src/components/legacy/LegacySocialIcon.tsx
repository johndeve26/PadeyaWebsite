import { normalizeSocialPlatform } from "@/lib/legacy-presentation";

/** Simple brand-neutral glyphs for About social links (presentation only). */
export function LegacySocialIcon({
  platform,
  className = "h-4 w-4",
}: {
  platform: string;
  className?: string;
}) {
  const key = normalizeSocialPlatform(platform);
  const common = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  switch (key) {
    case "instagram":
      return (
        <svg {...common}>
          <rect x="3" y="3" width="18" height="18" rx="5" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="17.5" cy="6.5" r="0.8" fill="currentColor" stroke="none" />
        </svg>
      );
    case "tiktok":
      return (
        <svg {...common}>
          <path d="M14 4v10.2a3.8 3.8 0 1 1-3.2-3.75V13a1.6 1.6 0 1 0 1.4 1.58V4h1.8Z" />
          <path d="M14 7.2c1.2 1.5 2.7 2.3 4.5 2.5" />
        </svg>
      );
    case "x":
      return (
        <svg {...common}>
          <path d="M5 5 19 19M19 5 5 19" />
        </svg>
      );
    case "youtube":
      return (
        <svg {...common}>
          <rect x="3" y="6" width="18" height="12" rx="3" />
          <path d="M11 9.5v5l4.5-2.5L11 9.5Z" fill="currentColor" stroke="none" />
        </svg>
      );
    case "spotify":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 10.2c2.4-1 5.5-.8 7.8.4M8.5 13c1.9-.7 4.3-.6 6.2.3M9 15.6c1.4-.5 3.1-.4 4.5.2" />
        </svg>
      );
    case "mixcloud":
      return (
        <svg {...common}>
          <path d="M4 14.5V12a2 2 0 0 1 4 0v2.5M10 14.5V9.5a2 2 0 0 1 4 0v5M16 14.5V11a2 2 0 0 1 4 0v3.5" />
        </svg>
      );
    case "website":
    default:
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3c2.5 2.8 3.8 5.8 3.8 9S14.5 18.2 12 21c-2.5-2.8-3.8-5.8-3.8-9S9.5 5.8 12 3Z" />
        </svg>
      );
  }
}
