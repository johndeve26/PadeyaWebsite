"use client";

import Link from "next/link";
import { useState } from "react";

import { MessagesMobileHomeLink } from "@/components/messaging/MessagesMobileHomeLink";
import { ParticipantAvatar } from "@/components/messaging/ParticipantAvatar";
import { GenderBadge } from "@/components/profile/GenderBadge";
import { Badge, Button, Drawer } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import type { ThreadDetail } from "@/lib/types/messaging";

type Props = {
  detail: ThreadDetail;
  mode: "fan" | "host";
  basePath: string;
  searchOpen: boolean;
  onToggleSearch: () => void;
  onArchive: () => void;
  onBlock: () => void;
  onReport: () => void;
  onAcceptRequest?: () => void;
};

/** One-row thread title bar on small screens — details live in the actions sheet. */
export function ThreadMobileHeaderBar({
  detail,
  mode,
  basePath,
  searchOpen,
  onToggleSearch,
  onArchive,
  onBlock,
  onReport,
  onAcceptRequest,
}: Props) {
  const [actionsOpen, setActionsOpen] = useState(false);
  const profileHref =
    detail.counterpart.legacy_path || detail.counterpart.passport_path;

  const subtitle =
    detail.connect_context?.context_label ||
    (detail.connect_context?.badge ? detail.connect_context.badge : null) ||
    (detail.counterpart.username ? `@${detail.counterpart.username}` : null);

  return (
    <>
      <div className="flex shrink-0 items-center gap-1.5 border-b border-border px-2 py-2 md:hidden">
        <MessagesMobileHomeLink mode={mode} />
        <Link
          href={basePath}
          className="shrink-0 rounded-[var(--radius-sm)] border border-border bg-surface-muted/80 px-2 py-1 text-[11px] font-bold text-muted-foreground dark:bg-surface-inset/80"
          aria-label="Back to inbox list"
        >
          Inbox
        </Link>
        <ParticipantAvatar
          name={detail.counterpart.display_name}
          avatarUrl={detail.counterpart.avatar_url}
          size="sm"
        />
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-1.5">
            <p className="truncate text-sm font-extrabold text-heading">
              {detail.counterpart.display_name}
            </p>
            {detail.counterpart.gender_visible &&
            detail.counterpart.gender_short ? (
              <GenderBadge
                value={{
                  gender: detail.counterpart.gender ?? null,
                  gender_short: detail.counterpart.gender_short,
                  gender_label: detail.counterpart.gender_label ?? null,
                  gender_visible: detail.counterpart.gender_visible,
                }}
              />
            ) : null}
          </div>
          {subtitle ? (
            <p className="truncate text-[11px] text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>
        <Button
          type="button"
          size="sm"
          variant={searchOpen ? "primary" : "secondary"}
          className="shrink-0 px-2.5"
          onClick={onToggleSearch}
          aria-pressed={searchOpen}
        >
          Search
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="shrink-0 px-2.5"
          onClick={() => setActionsOpen(true)}
        >
          More
        </Button>
      </div>

      <Drawer
        open={actionsOpen}
        onClose={() => setActionsOpen(false)}
        title={detail.counterpart.display_name}
        description="Thread actions and details"
        footer={
          <div className="flex flex-col gap-2">
            {detail.is_request && mode === "host" && onAcceptRequest ? (
              <Button
                size="sm"
                onClick={() => {
                  setActionsOpen(false);
                  onAcceptRequest();
                }}
              >
                Accept request
              </Button>
            ) : null}
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setActionsOpen(false);
                onArchive();
              }}
            >
              Archive
            </Button>
            {detail.counterpart_user_id && !detail.blocked ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setActionsOpen(false);
                  onBlock();
                }}
              >
                Block
              </Button>
            ) : null}
            <Button
              size="sm"
              variant="danger"
              onClick={() => {
                setActionsOpen(false);
                onReport();
              }}
            >
              Report
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            {detail.thread_type === "fan_fan" || detail.connect_context ? (
              <Badge tone="accent" size="sm">
                {detail.connect_context?.badge || "Fan Connect"}
              </Badge>
            ) : detail.counterpart.role ? (
              <Badge tone="outline" size="sm">
                {detail.counterpart.role}
              </Badge>
            ) : null}
            {detail.is_request ? (
              <Badge tone="warning" size="sm">
                Request
              </Badge>
            ) : null}
            {detail.blocked ? (
              <Badge tone="danger" size="sm">
                Blocked
              </Badge>
            ) : null}
          </div>
          {profileHref ? (
            <Link
              href={profileHref}
              className="block text-sm font-semibold text-foreground underline-offset-2 hover:underline"
              onClick={() => setActionsOpen(false)}
            >
              View profile
            </Link>
          ) : null}
          <p className="text-xs text-muted-foreground">
            Started {formatDateTime(detail.created_at)}
          </p>
        </div>
      </Drawer>
    </>
  );
}
