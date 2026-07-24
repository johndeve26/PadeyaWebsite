"use client";

import Link from "next/link";

import { Alert, Badge, Button, Card } from "@/components/ui";
import { PushInstallDetails } from "@/components/notifications/PushInstallDetails";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { formatDateTime } from "@/lib/format";
import type { PushSubscriptionDevice } from "@/lib/notifications-api";
import {
  PUSH_UI_STATUS,
  resolvePushUiStatus,
  UNSUPPORTED_PUSH_HELPER,
  type PushUiStatus,
} from "@/lib/push-device";

function deviceLastActive(device: PushSubscriptionDevice): string | null {
  return device.last_success_at || device.updated_at || device.created_at || null;
}

function statusBadgeTone(
  tone: (typeof PUSH_UI_STATUS)[PushUiStatus]["tone"],
): "success" | "warning" | "danger" | "neutral" | "accent" {
  return tone;
}

/**
 * Compact push status card for notification settings.
 * Permission is requested only after Enable — never on load.
 */
export function PushSettingsPanel() {
  const push = usePushNotifications();
  const activeDevices = push.devices.filter((d) => d.is_active);
  const { isAppleMobile, isStandalone, needsHomeScreenForPush } = push.device;

  const status = resolvePushUiStatus({
    supported: push.supported,
    adminEnabled: push.adminEnabled,
    permission: push.permission,
    subscribed: push.subscribed,
    activeDeviceCount: activeDevices.length,
    deviceCount: push.devices.length,
    needsHomeScreenForPush,
    isStandalone,
  });
  const meta = PUSH_UI_STATUS[status];

  const canEnable =
    (status === "not_enabled" || status === "no_active_device") &&
    push.supported &&
    push.adminEnabled &&
    !push.busy;

  const showDevices = push.devices.length > 0;
  const showInstallDetails =
    status === "install_required" || status === "unsupported";

  return (
    <Card className="min-w-0 space-y-4 overflow-hidden p-4 sm:p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <h3 className="font-bold text-foreground">Push notifications</h3>
          <p className="text-sm text-muted-foreground">
            System alerts on this device even when Pàdéyá is closed. Separate
            from in-app toasts.
          </p>
        </div>
        <Badge tone={statusBadgeTone(meta.tone)} size="sm" className="shrink-0">
          {meta.label}
        </Badge>
      </div>

      <p className="min-w-0 text-sm leading-relaxed text-foreground">{meta.body}</p>

      {push.error ? (
        <Alert tone="danger" title="Could not update">
          {push.error}
        </Alert>
      ) : null}

      {push.note && status !== "enabled" ? (
        <Alert tone="success" title="Updated">
          {push.note}
        </Alert>
      ) : null}

      {showInstallDetails ? (
        <PushInstallDetails
          variant={
            status === "install_required" ||
            (status === "unsupported" && isAppleMobile && !isStandalone)
              ? "ios"
              : "generic"
          }
        />
      ) : null}

      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap">
        {canEnable ? (
          <Button
            className="w-full sm:w-auto"
            size="sm"
            disabled={!canEnable}
            onClick={() => void push.enable()}
          >
            {push.busy ? "Enabling…" : "Enable notifications"}
          </Button>
        ) : null}

        {status === "enabled" ? (
          <Button
            className="w-full sm:w-auto"
            size="sm"
            variant="secondary"
            disabled={push.busy}
            onClick={() => void push.disableThisDevice()}
          >
            Disable on this device
          </Button>
        ) : null}

        {status === "unsupported" || status === "install_required" ? (
          <Link
            href={UNSUPPORTED_PUSH_HELPER.centerHref}
            className="inline-flex w-full sm:w-auto"
          >
            <Button className="w-full sm:w-auto" size="sm" variant="secondary">
              Open notification center
            </Button>
          </Link>
        ) : null}
      </div>

      {showDevices ? (
        <div className="min-w-0 space-y-2 border-t border-border pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Devices ({activeDevices.length} active)
          </p>
          <ul className="min-w-0 space-y-2">
            {push.devices.map((device) => {
              const lastActive = deviceLastActive(device);
              return (
                <li
                  key={device.id}
                  className="flex min-w-0 flex-col gap-2 rounded-md border border-border/80 bg-muted/20 px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">
                      {device.device_label || device.platform || "Browser"}
                      {!device.is_active ? (
                        <span className="ml-2 text-xs font-normal text-muted-foreground">
                          inactive
                        </span>
                      ) : null}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {[
                        device.platform,
                        lastActive
                          ? `Last active ${formatDateTime(lastActive)}`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  {device.is_active ? (
                    <Button
                      className="w-full shrink-0 sm:w-auto"
                      size="sm"
                      variant="ghost"
                      disabled={push.busy}
                      onClick={() => void push.removeDevice(device.id)}
                    >
                      Remove
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </Card>
  );
}
