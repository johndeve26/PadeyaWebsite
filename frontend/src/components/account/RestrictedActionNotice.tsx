"use client";

import { Alert } from "@/components/ui";
import { USER_RESTRICTION_ACTION_MESSAGE } from "@/lib/user-restrictions";

/** Safe end-user notice — never shows admin reason or internal notes. */
export function RestrictedActionNotice({
  className = "",
  message = USER_RESTRICTION_ACTION_MESSAGE,
}: {
  className?: string;
  message?: string;
}) {
  return (
    <Alert tone="warning" title="Unavailable" className={className}>
      {message}
    </Alert>
  );
}
