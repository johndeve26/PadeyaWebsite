"use client";

import type { ElementType, ReactNode } from "react";

import {
  useTrackImpression,
  type UseTrackImpressionOptions,
} from "@/hooks/useTrackImpression";
import { cn } from "@/lib/cn";

type TrackImpressionProps = UseTrackImpressionOptions & {
  children: ReactNode;
  className?: string;
  as?: "div" | "span" | "li" | "article" | "section";
};

/**
 * Wrap listing cards (or any block) to track impressions via IntersectionObserver.
 * Threshold: ≥50% visible for ≥500ms; deduped per event/list/session.
 */
export function TrackImpression({
  children,
  className,
  as = "div",
  ...options
}: TrackImpressionProps) {
  const ref = useTrackImpression<HTMLElement>(options);
  const Tag = as as ElementType;

  return (
    <Tag ref={ref} className={cn(className)}>
      {children}
    </Tag>
  );
}
