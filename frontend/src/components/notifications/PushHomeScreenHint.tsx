"use client";

import { Alert } from "@/components/ui";
import { PushInstallDetails } from "@/components/notifications/PushInstallDetails";
import { IOS_PUSH_HELPER } from "@/lib/push-device";

type Props = {
  /** Show when iPhone/iPad is not running as the Home Screen / PWA app */
  show: boolean;
  className?: string;
};

/**
 * Compact iPhone/iPad install hint — steps live in expandable details.
 */
export function PushHomeScreenHint({ show, className }: Props) {
  if (!show) return null;

  return (
    <div className={className ? `min-w-0 space-y-2 ${className}` : "min-w-0 space-y-2"}>
      <Alert tone="info" title={IOS_PUSH_HELPER.title}>
        <p>{IOS_PUSH_HELPER.body}</p>
      </Alert>
      <PushInstallDetails variant="ios" />
    </div>
  );
}
