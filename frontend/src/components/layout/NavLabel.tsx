"use client";

import { useUnreadMessages } from "@/hooks/useUnreadMessages";
import { useUnreadNotifications } from "@/hooks/useUnreadNotifications";
import { cn } from "@/lib/cn";
import type { NavIconId, NavItem } from "@/lib/nav/workspace";

function UsersNavIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={cn("h-4 w-4 shrink-0", className)}
    >
      <circle
        cx="12"
        cy="8"
        r="3.25"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path
        d="M5.5 18.25c1.4-2.6 3.6-3.75 6.5-3.75s5.1 1.15 6.5 3.75"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

function NavIcon({ id, active }: { id: NavIconId; active?: boolean }) {
  if (id === "users") {
    return (
      <UsersNavIcon
        className={active ? "text-paper" : "text-muted-foreground"}
      />
    );
  }
  return null;
}

export function NavLabel({
  item,
  active,
}: {
  item: NavItem;
  active?: boolean;
}) {
  // Only the matching badge subscribes — every NavLabel used to poll both.
  const messagesUnread = useUnreadMessages(item.badge === "messages");
  const notificationsUnread = useUnreadNotifications(
    item.badge === "notifications",
  );
  const unread =
    item.badge === "messages"
      ? messagesUnread
      : item.badge === "notifications"
        ? notificationsUnread
        : 0;

  const label = (
    <span className="inline-flex min-w-0 items-center gap-2">
      {item.icon ? <NavIcon id={item.icon} active={active} /> : null}
      <span className="min-w-0 truncate">{item.label}</span>
    </span>
  );

  if (!item.badge || unread < 1) {
    return label;
  }

  return (
    <>
      <span className="min-w-0 flex-1 truncate">
        <span className="inline-flex min-w-0 items-center gap-2">
          {item.icon ? <NavIcon id={item.icon} active={active} /> : null}
          <span className="min-w-0 truncate">{item.label}</span>
        </span>
      </span>
      <span className="inline-flex min-w-5 shrink-0 items-center justify-center rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-extrabold text-primary-foreground">
        {unread > 99 ? "99+" : unread}
      </span>
    </>
  );
}
