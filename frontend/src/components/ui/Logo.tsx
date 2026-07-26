import Image from "next/image";
import Link from "next/link";

import { brand, type LogoVariant } from "@/lib/brand";

export type LogoProps = {
  /**
   * `dark` — light mark on ink/dark surfaces.
   * `light` — dark mark on paper/light surfaces.
   * `auto` — CSS `.dark` class (no hydration mismatch).
   */
  variant?: LogoVariant | "auto";
  href?: string;
  priority?: boolean;
  className?: string;
  height?: number;
};

export function Logo({
  variant = "light",
  href,
  priority = false,
  className = "",
  height = 36,
}: LogoProps) {
  // Official lockups are ~1024×327
  const width = Math.round(height * (1024 / 337));
  // undefined → home link; "" / null-ish → bare image (parent may wrap its own Link)
  const resolvedHref = href === undefined ? "/" : href;

  // Explicit width+height (not width:auto) — footer/header CLS was attributed to
  // "Media element lacking an explicit size" when only height was fixed.
  const imageClass = ["block max-w-full", className].filter(Boolean).join(" ");

  const renderImage = (
    logoVariant: LogoVariant,
    extraClass = "",
    imagePriority = false,
  ) => (
    <Image
      src={brand.logos[logoVariant]}
      alt={brand.name}
      width={width}
      height={height}
      priority={imagePriority}
      unoptimized
      className={[imageClass, extraClass].filter(Boolean).join(" ")}
      style={{ width, height }}
    />
  );

  const image =
    variant === "auto" ? (
      <span className="inline-flex">
        {renderImage("light", "dark:hidden", priority)}
        {renderImage("dark", "hidden dark:block", false)}
      </span>
    ) : (
      renderImage(variant, "", priority)
    );

  if (!resolvedHref) {
    return image;
  }

  return (
    <Link
      href={resolvedHref}
      aria-label={`${brand.name} home`}
      className="inline-flex"
    >
      {image}
    </Link>
  );
}
