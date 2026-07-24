"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import { ScrollHintNav } from "@/components/ui/ScrollHintNav";
import { userHasPermission } from "@/lib/auth/permissions";
import { cn } from "@/lib/cn";

const LINKS = [
  {
    href: (eventId: string) => `/host/events/${eventId}/merchandise`,
    match: (pathname: string, eventId: string) => {
      const root = `/host/events/${eventId}/merchandise`;
      if (pathname === root || pathname === `${root}/`) return true;
      if (pathname.startsWith(`${root}/new`)) return true;
      const escaped = root.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`^${escaped}/[^/]+/edit(?:/|$)`).test(pathname);
    },
    label: "Products",
    anyOf: ["merch.manage_own"] as const,
  },
  {
    href: (eventId: string) => `/host/events/${eventId}/bundles`,
    match: (pathname: string, eventId: string) =>
      pathname.startsWith(`/host/events/${eventId}/bundles`),
    label: "Bundles",
    anyOf: ["merch.manage_own"] as const,
  },
  {
    href: (eventId: string) => `/host/events/${eventId}/post-event-drops`,
    match: (pathname: string, eventId: string) =>
      pathname.startsWith(`/host/events/${eventId}/post-event-drops`),
    label: "Post-event drops",
    anyOf: ["merch.manage_own"] as const,
  },
  {
    href: (eventId: string) => `/host/events/${eventId}/merchandise/orders`,
    match: (pathname: string, eventId: string) =>
      pathname.startsWith(`/host/events/${eventId}/merchandise/orders`),
    label: "Orders",
    anyOf: ["merch.manage_own", "merch.view_fulfillment", "merch.fulfill"] as const,
  },
  {
    href: (eventId: string) => `/host/events/${eventId}/merchandise/fulfillment`,
    match: (pathname: string, eventId: string) =>
      pathname.startsWith(`/host/events/${eventId}/merchandise/fulfillment`),
    label: "Fulfillment",
    anyOf: ["merch.view_fulfillment", "merch.fulfill", "merch.manage_own"] as const,
  },
] as const;

export function EventMerchSubnav({ eventId }: { eventId: string }) {
  const pathname = usePathname() || "";
  const { user } = useAuth();

  const links = LINKS.filter((link) =>
    userHasPermission(user, ...(link.anyOf as unknown as string[])),
  );

  if (links.length === 0) return null;

  return (
    <ScrollHintNav
      aria-label="Event merchandise"
      className="mb-4 mt-3 border-b border-border pb-px"
      scrollClassName="flex min-w-0 gap-1"
    >
      {links.map((link) => {
        const href = link.href(eventId);
        const active = link.match(pathname, eventId);
        return (
          <Link
            key={link.label}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "shrink-0 rounded-t-md px-3 py-2 text-sm font-semibold transition-colors",
              active
                ? "border-b-2 border-[var(--brand-green)] text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </ScrollHintNav>
  );
}
