import { type HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Width = "default" | "narrow" | "wide" | "profile" | "full";

export type ContainerProps = HTMLAttributes<HTMLDivElement> & {
  width?: Width;
};

/** Site content rail — keep page sections on one shared max-width. */
export const SITE_CONTENT_MAX = "max-w-7xl";

const widthClasses: Record<Width, string> = {
  narrow: "max-w-3xl",
  /** Primary marketing / app content rail */
  default: SITE_CONTENT_MAX,
  /** Alias of default — prefer omitting `width` for new code */
  wide: SITE_CONTENT_MAX,
  /** Legacy public profile — wider without stretching other layouts */
  profile: "max-w-[1440px]",
  /** Private dashboards / workspaces — use the full viewport width */
  full: "max-w-none",
};

export function Container({
  width = "default",
  className = "",
  ...props
}: ContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 sm:px-6 lg:px-8",
        widthClasses[width],
        className,
      )}
      {...props}
    />
  );
}
