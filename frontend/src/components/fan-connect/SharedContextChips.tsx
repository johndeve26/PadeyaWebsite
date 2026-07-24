"use client";

import Link from "next/link";

import { Badge } from "@/components/ui";
import type { SharedContext } from "@/lib/types/fan-connect";

type Props = {
  context: SharedContext;
  className?: string;
};

export function SharedContextChips({ context, className = "" }: Props) {
  const events = context.events ?? [];
  const hosts = context.hosts ?? [];
  const categories = context.categories ?? [];
  const has =
    events.length > 0 || hosts.length > 0 || categories.length > 0;
  if (!has) return null;

  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`}>
      {events.slice(0, 3).map((ev) => (
        <Link key={ev.event_id} href={ev.path}>
          <Badge tone="outline" size="sm">
            {ev.title}
            {ev.city ? ` · ${ev.city}` : ""}
          </Badge>
        </Link>
      ))}
      {hosts.slice(0, 3).map((h) => (
        <Badge key={h.host_id} tone="outline" size="sm">
          {h.display_name}
        </Badge>
      ))}
      {categories.slice(0, 3).map((c) => (
        <Badge key={c} tone="accent" size="sm">
          {c}
        </Badge>
      ))}
    </div>
  );
}
