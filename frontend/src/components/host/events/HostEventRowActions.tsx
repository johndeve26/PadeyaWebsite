"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { Dropdown, type DropdownItem } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { EventItem } from "@/lib/types/events";

import type { EventRowActions } from "./event-list-types";

type ActionLink = {
  id: string;
  label: string;
  href?: string;
  onClick?: () => void;
  primary?: boolean;
};

function RowAction({
  href,
  label,
  onClick,
  primary,
}: {
  href?: string;
  label: string;
  onClick?: () => void;
  primary?: boolean;
}) {
  const className = cn(
    "rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.05em] whitespace-nowrap transition-colors",
    primary
      ? "bg-primary text-primary-foreground shadow-[var(--shadow-soft)] hover:bg-primary-hover"
      : "bg-muted text-muted-foreground hover:bg-surface-muted hover:text-foreground",
  );
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {label}
      </button>
    );
  }
  if (!href) return null;
  return (
    <Link href={href} className={className}>
      {label}
    </Link>
  );
}

function buildAllActions(
  event: EventItem,
  actions: EventRowActions,
  onView: (event: EventItem) => void,
  hideEdit?: boolean,
): ActionLink[] {
  const id = event.id;

  if (actions.scannerOnly) {
    const links: ActionLink[] = [];
    if (actions.canView) {
      links.push({ id: "view", label: "View", onClick: () => onView(event) });
    }
    if (actions.canScanner) {
      links.push({
        id: "scanner",
        label: "Scanner",
        href: `/host/events/${id}/check-in`,
        primary: true,
      });
    }
    return links;
  }

  if (actions.merchOnly) {
    if (!actions.canMerch) return [];
    return [
      {
        id: "pickup",
        label: "Pickup",
        href: `/host/events/${id}/merchandise/fulfillment`,
        primary: true,
      },
      {
        id: "merch",
        label: "Merch Studio",
        href: `/host/events/${id}/merchandise`,
      },
    ];
  }

  const links: ActionLink[] = [];

  if (actions.canView) {
    links.push({ id: "view", label: "View", onClick: () => onView(event) });
  }
  if (!hideEdit && !actions.deskOnly && actions.canEdit) {
    links.push({
      id: "edit",
      label: "Edit event",
      href: `/host/events/${id}/edit`,
      primary: true,
    });
  }
  if (!actions.deskOnly && actions.canTickets) {
    links.push({ id: "tickets", label: "Tickets", href: `/host/events/${id}/tickets` });
  }
  if (actions.canScanner) {
    links.push({
      id: "scanner",
      label: "Scanner",
      href: `/host/events/${id}/check-in`,
      // Green CTA when Edit is already next to the title, or for desk staff.
      primary: Boolean(hideEdit) || actions.deskOnly,
    });
  }
  // Post-night primary surface — hosts upload/recap from Memories.
  if (!actions.deskOnly && !actions.scannerOnly && !actions.merchOnly) {
    links.push({
      id: "memories",
      label: "Memories",
      href: `/host/events/${id}/memory`,
      primary: event.status === "completed",
    });
  }
  if (!actions.deskOnly && actions.canMerch) {
    links.push({
      id: "merch",
      label: "Merch Studio",
      href: `/host/events/${id}/merchandise`,
    });
  }
  if (actions.deskOnly && actions.canMerch) {
    links.push({
      id: "pickup",
      label: "Pickup",
      href: `/host/events/${id}/merchandise/fulfillment`,
    });
  }
  if (!actions.deskOnly && actions.canAmbassadors) {
    links.push({
      id: "ambassadors",
      label: "Ambassador Campaigns",
      href: `/host/events/${id}/ambassadors`,
    });
  }
  if (!actions.deskOnly && actions.canAnalytics) {
    links.push({
      id: "analytics",
      label: "Analytics",
      href: `/host/events/${id}/analytics`,
    });
  }
  if (!actions.deskOnly) {
    links.push({ id: "hub", label: "Hub", href: `/host/events/${id}` });
  }

  return links;
}

function primaryCandidateOrder(
  event: EventItem,
  actions: EventRowActions,
  hideEdit?: boolean,
): string[] {
  if (actions.scannerOnly) return ["view", "scanner"];
  if (actions.merchOnly) return ["pickup", "merch"];
  if (actions.deskOnly) return ["scanner", "pickup", "view"];
  // After the night ends, Memories + View stay inline; Edit lands in overflow.
  if (event.status === "completed") return ["memories", "view", "hub"];
  if (hideEdit) return ["scanner", "view", "tickets"];
  // Edit always first and always inline when available.
  return ["edit", "scanner", "view"];
}

function splitActions(
  all: ActionLink[],
  event: EventItem,
  actions: EventRowActions,
  hideEdit?: boolean,
): { primary: ActionLink[]; overflow: ActionLink[] } {
  if (actions.scannerOnly || actions.merchOnly) {
    return { primary: all, overflow: [] };
  }

  const order = primaryCandidateOrder(event, actions, hideEdit);
  const primaryIds: string[] = [];
  for (const id of order) {
    if (primaryIds.length >= 2) break;
    if (all.some((action) => action.id === id)) primaryIds.push(id);
  }

  // Prefer keeping Edit out of the overflow menu entirely.
  const primaryIdSet = new Set(primaryIds);
  const primary = primaryIds
    .map((id) => all.find((action) => action.id === id))
    .filter((action): action is ActionLink => Boolean(action));
  const overflow = all.filter((action) => !primaryIdSet.has(action.id));
  return { primary, overflow };
}

function toDropdownItems(
  overflow: ActionLink[],
  router: ReturnType<typeof useRouter>,
): DropdownItem[] {
  return overflow.map((action) => ({
    id: action.id,
    label: action.label,
    onSelect: () => {
      if (action.onClick) {
        action.onClick();
        return;
      }
      if (action.href) router.push(action.href);
    },
  }));
}

type Props = {
  event: EventItem;
  actions: EventRowActions;
  onView: (event: EventItem) => void;
  compact?: boolean;
  /** When Edit is already shown next to the title, omit it from the action row. */
  hideEdit?: boolean;
};

export function HostEventRowActions({
  event,
  actions,
  onView,
  compact,
  hideEdit,
}: Props) {
  const router = useRouter();

  const { primary, overflow } = useMemo(() => {
    const all = buildAllActions(event, actions, onView, hideEdit);
    return splitActions(all, event, actions, hideEdit);
  }, [event, actions, onView, hideEdit]);

  const menuItems = useMemo(
    () => toDropdownItems(overflow, router),
    [overflow, router],
  );

  if (primary.length === 0 && menuItems.length === 0) return null;

  return (
    <div
      className={cn(
        "flex min-w-0 max-w-full shrink-0 flex-nowrap items-center gap-1.5",
        compact ? "" : "justify-end",
      )}
    >
      {primary.map((action) => (
        <RowAction
          key={action.id}
          href={action.href}
          label={action.label}
          onClick={action.onClick}
          primary={action.primary}
        />
      ))}
      {menuItems.length > 0 ? (
        <Dropdown
          label="⋯ Actions"
          align="right"
          items={menuItems}
          className="shrink-0"
        />
      ) : null}
    </div>
  );
}
