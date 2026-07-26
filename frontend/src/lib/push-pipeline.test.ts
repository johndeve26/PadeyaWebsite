import { describe, expect, it } from "vitest";

import {
  buildPushDiagnosticLines,
  resolvePushPipelineState,
  resolvePushUiStatus,
} from "@/lib/push-device";
import {
  endpointMatchesHint,
  subscriptionKeysComplete,
  urlBase64ToUint8Array,
} from "@/lib/push-subscription";
import { safePushActionUrl } from "@/lib/push-url";

describe("push pipeline status", () => {
  it("does not treat permission granted alone as subscribed", () => {
    const pipeline = resolvePushPipelineState({
      supported: true,
      adminEnabled: true,
      permission: "granted",
      subscribed: false,
      serverRegisteredHere: false,
      activeDeviceCount: 0,
      needsHomeScreenForPush: false,
      isStandalone: false,
      serviceWorkerActive: true,
    });
    expect(pipeline).toBe("permission_granted_not_subscribed");

    const ui = resolvePushUiStatus({
      supported: true,
      adminEnabled: true,
      permission: "granted",
      subscribed: false,
      serverRegisteredHere: false,
      activeDeviceCount: 0,
      deviceCount: 0,
      needsHomeScreenForPush: false,
      isStandalone: false,
      serviceWorkerActive: true,
    });
    expect(ui).toBe("permission_granted_not_subscribed");
    expect(ui).not.toBe("enabled");
  });

  it("marks local subscription without server row as stale", () => {
    expect(
      resolvePushPipelineState({
        supported: true,
        adminEnabled: true,
        permission: "granted",
        subscribed: true,
        serverRegisteredHere: false,
        activeDeviceCount: 1,
        needsHomeScreenForPush: false,
        isStandalone: true,
        serviceWorkerActive: true,
      }),
    ).toBe("subscription_stale");
  });

  it("requires local + server registration for subscribed", () => {
    expect(
      resolvePushPipelineState({
        supported: true,
        adminEnabled: true,
        permission: "granted",
        subscribed: true,
        serverRegisteredHere: true,
        activeDeviceCount: 1,
        needsHomeScreenForPush: false,
        isStandalone: true,
        serviceWorkerActive: true,
      }),
    ).toBe("subscribed");
    expect(
      resolvePushUiStatus({
        supported: true,
        adminEnabled: true,
        permission: "granted",
        subscribed: true,
        serverRegisteredHere: true,
        activeDeviceCount: 1,
        deviceCount: 1,
        needsHomeScreenForPush: false,
        isStandalone: true,
        serviceWorkerActive: true,
      }),
    ).toBe("enabled");
  });

  it("detects unsupported and permission denied", () => {
    expect(
      resolvePushPipelineState({
        supported: false,
        adminEnabled: true,
        permission: "default",
        subscribed: false,
        serverRegisteredHere: false,
        activeDeviceCount: 0,
        needsHomeScreenForPush: false,
        isStandalone: false,
        serviceWorkerActive: false,
      }),
    ).toBe("unsupported");
    expect(
      resolvePushPipelineState({
        supported: true,
        adminEnabled: true,
        permission: "denied",
        subscribed: false,
        serverRegisteredHere: false,
        activeDeviceCount: 0,
        needsHomeScreenForPush: false,
        isStandalone: false,
        serviceWorkerActive: true,
      }),
    ).toBe("permission_denied");
  });

  it("builds diagnostic lines without secrets", () => {
    const lines = buildPushDiagnosticLines({
      permission: "granted",
      serviceWorkerActive: true,
      subscribed: false,
      serverRegisteredHere: false,
    });
    expect(lines).toEqual({
      permission: "Allowed",
      serviceWorker: "Active",
      thisDevice: "Not subscribed",
      serverRegistration: "Missing",
    });
    expect(JSON.stringify(lines)).not.toMatch(/p256dh|auth|endpoint/i);
  });
});

describe("push subscription helpers", () => {
  it("rejects missing VAPID public key", () => {
    expect(() => urlBase64ToUint8Array("")).toThrow(/Missing VAPID public key/);
    expect(() => urlBase64ToUint8Array("   ")).toThrow(/Missing VAPID public key/);
  });

  it("converts url-safe base64 VAPID keys", () => {
    // 65-byte uncompressed EC point → typical VAPID public key shape
    const key =
      "BEaGFEGREdXWHH-MkMsOIVrXiunX3LnbBmIeoUSn_deBGpT8h2VXH0Lpht8Bv_XCYE7MiJW9Wq8UxaLm6q03dXY";
    const bytes = urlBase64ToUint8Array(key);
    expect(bytes.byteLength).toBeGreaterThan(60);
    expect(bytes[0]).toBe(4);
  });

  it("validates subscription JSON completeness", () => {
    expect(
      subscriptionKeysComplete({
        endpoint: "https://push.example/x",
        keys: { p256dh: "a", auth: "b" },
      }),
    ).toBe(true);
    expect(subscriptionKeysComplete({ endpoint: "https://x", keys: {} })).toBe(
      false,
    );
  });

  it("matches endpoint hints safely", () => {
    const endpoint = "https://fcm.googleapis.com/fcm/send/abcdefghijklmnopqrstuvwxyz";
    expect(endpointMatchesHint(endpoint, "…ijklmnopqrstuvwxyz")).toBe(true);
    expect(endpointMatchesHint(endpoint, "…nope")).toBe(false);
    expect(endpointMatchesHint(endpoint, null)).toBe(false);
    expect(endpointMatchesHint(endpoint, "…short")).toBe(false);
  });
});

describe("push action URL validation", () => {
  it("allows internal padeya paths only", () => {
    expect(safePushActionUrl("/dashboard/notifications")).toBe(
      "/dashboard/notifications",
    );
    expect(safePushActionUrl("/dashboard/tickets?id=1")).toBe(
      "/dashboard/tickets?id=1",
    );
  });

  it("blocks external and unsafe destinations", () => {
    expect(safePushActionUrl("https://evil.example/phish")).toBe(
      "/dashboard/notifications",
    );
    expect(safePushActionUrl("javascript:alert(1)")).toBe(
      "/dashboard/notifications",
    );
    expect(safePushActionUrl("/vault/secret")).toBe("/dashboard/notifications");
    expect(safePushActionUrl("/checkout/pay")).toBe("/dashboard/notifications");
  });
});
