"use client";

import { Badge } from "@/components/ui";
import {
  deriveSettingStatus,
  sourceLabel,
  sourceTone,
  type DerivedSettingStatus,
} from "@/lib/runtime-settings-display";
import type { RuntimeSettingItem } from "@/lib/runtime-settings-api";

type Props = {
  source?: string | null;
  /** Full item — when provided, also renders derived status badge. */
  item?: Pick<
    RuntimeSettingItem,
    "status" | "source" | "configured" | "enabled" | "is_secret" | "value"
  >;
  showStatus?: boolean;
  className?: string;
};

export function RuntimeSettingSourceBadge({
  source,
  item,
  showStatus = true,
  className = "",
}: Props) {
  const src = source ?? item?.source;
  const status: DerivedSettingStatus | null = item
    ? deriveSettingStatus(item)
    : null;

  return (
    <span className={`inline-flex flex-wrap items-center gap-1.5 ${className}`}>
      <Badge tone={sourceTone(src)} size="sm">
        {sourceLabel(src)}
      </Badge>
      {showStatus && status ? (
        <Badge tone={status.tone} size="sm">
          {status.label}
        </Badge>
      ) : null}
    </span>
  );
}
