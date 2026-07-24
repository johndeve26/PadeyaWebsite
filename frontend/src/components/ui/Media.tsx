import { cn } from "@/lib/cn";
import { resolveMediaUrl } from "@/lib/media";

/** Local-friendly media — works with demo SVGs without next/image SVG config. */
export function Media({
  src,
  alt = "",
  className = "",
}: {
  src: string;
  alt?: string;
  className?: string;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={resolveMediaUrl(src)}
      alt={alt}
      className={cn("h-full w-full object-cover", className)}
      loading="lazy"
    />
  );
}
