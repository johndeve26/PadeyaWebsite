"use client";

import Link from "next/link";

import { Alert, Button } from "@/components/ui";
import { PushInstallDetails } from "@/components/notifications/PushInstallDetails";
import { UNSUPPORTED_PUSH_HELPER } from "@/lib/push-device";

type Props = {
  show: boolean;
  preferHomeScreenSteps?: boolean;
  className?: string;
};

/**
 * Unsupported browser push state — never prompts for browser permission.
 */
export function PushUnsupportedState({
  show,
  preferHomeScreenSteps = false,
  className,
}: Props) {
  if (!show) return null;

  return (
    <div className={className ? `min-w-0 space-y-3 ${className}` : "min-w-0 space-y-3"}>
      <Alert tone="info" title={UNSUPPORTED_PUSH_HELPER.title}>
        <p>{UNSUPPORTED_PUSH_HELPER.body}</p>
      </Alert>
      <div className="flex min-w-0 flex-col gap-2 sm:flex-row">
        <Link
          href={UNSUPPORTED_PUSH_HELPER.centerHref}
          className="inline-flex w-full sm:w-auto"
        >
          <Button className="w-full sm:w-auto" size="sm" variant="secondary">
            {UNSUPPORTED_PUSH_HELPER.openCenterLabel}
          </Button>
        </Link>
      </div>
      <PushInstallDetails
        variant={preferHomeScreenSteps ? "ios" : "generic"}
      />
    </div>
  );
}
