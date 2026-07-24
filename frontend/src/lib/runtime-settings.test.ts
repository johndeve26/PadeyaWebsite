import { describe, expect, it } from "vitest";

import {
  deriveCategoryStatus,
  deriveSettingStatus,
  formatSecretDisplay,
  sanitizePublicMessage,
  sourceLabel,
  specialistHrefFor,
} from "./runtime-settings-display";
import {
  canClearRuntimeOverrides,
  canEditRuntimeSecrets,
  canEditRuntimeSettings,
  canTestRuntimeIntegrations,
  canViewRuntimeAudit,
  canViewRuntimeSettings,
  canViewRuntimeSystemStatus,
  getRuntimeSettingsCapabilities,
} from "./runtime-settings-permissions";
import type { User } from "./auth/types";

function user(partial: Partial<User> & Pick<User, "permissions" | "roles">): User {
  return {
    id: "u1",
    email: "a@b.co",
    full_name: "Admin",
    is_active: true,
    is_verified: true,
    created_at: "2026-01-01T00:00:00Z",
    ...partial,
  };
}

describe("formatSecretDisplay", () => {
  it("shows Not configured when missing", () => {
    expect(formatSecretDisplay({ configured: false })).toBe("Not configured");
  });

  it("shows first4…last4 from API masked_value", () => {
    expect(
      formatSecretDisplay({
        configured: true,
        masked_value: "Configured · smtp…9911",
      }),
    ).toBe("Configured · smtp…9911");
  });

  it("builds fingerprint from first_four and last_four", () => {
    expect(
      formatSecretDisplay({
        configured: true,
        first_four: "pk_t",
        last_four: "adey",
      }),
    ).toBe("Configured · pk_t…adey");
  });

  it("never returns a long raw secret string", () => {
    const out = formatSecretDisplay({
      configured: true,
      masked_value: "sk_live_this_is_a_very_long_secret_value_abcdef",
    });
    expect(out.startsWith("Configured")).toBe(true);
    expect(out.includes("sk_live_this_is_a_very_long")).toBe(false);
  });
});

describe("deriveSettingStatus / source badges", () => {
  it("maps API status when present", () => {
    expect(
      deriveSettingStatus({
        status: "db_override",
        source: "env",
        configured: true,
        is_secret: false,
        value: 1,
      }).label,
    ).toBe("Using DB override");
  });

  it("derives env fallback and db override from source", () => {
    expect(
      deriveSettingStatus({
        source: "env",
        configured: true,
        is_secret: false,
        value: true,
      }).status,
    ).toBe("env_fallback");
    expect(
      deriveSettingStatus({
        source: "db",
        configured: true,
        is_secret: false,
        value: true,
      }).status,
    ).toBe("db_override");
  });

  it("marks disabled and missing secrets", () => {
    expect(
      deriveSettingStatus({
        source: "env",
        enabled: false,
        configured: true,
        is_secret: false,
        value: 1,
      }).status,
    ).toBe("disabled");
    expect(
      deriveSettingStatus({
        source: "default",
        configured: false,
        is_secret: true,
        value: null,
      }).status,
    ).toBe("missing");
  });

  it("labels sources for badges", () => {
    expect(sourceLabel("db")).toBe("DB");
    expect(sourceLabel("env")).toBe("ENV");
    expect(sourceLabel("default")).toBe("Default");
  });

  it("derives category card status", () => {
    expect(
      deriveCategoryStatus({
        configured: false,
        enabled: true,
        source: "env",
      }).label,
    ).toBe("Needs configuration");
  });
});

describe("specialist email/push wiring", () => {
  it("points email and push at existing specialist pages", () => {
    expect(specialistHrefFor("email")).toBe("/admin/email/settings");
    expect(specialistHrefFor("push")).toBe("/admin/push/settings");
    expect(specialistHrefFor("ai")).toBeNull();
  });
});

describe("sanitizePublicMessage", () => {
  it("redacts secret-looking blobs from toasts/errors", () => {
    const msg = sanitizePublicMessage(
      "failed with sk_live_abcdefghijklmnopqrstuvwxyz012345",
    );
    expect(msg.includes("sk_live_abcdefghijklmnopqrstuvwxyz012345")).toBe(false);
    expect(msg.includes("[redacted]")).toBe(true);
  });
});

describe("runtime settings permissions", () => {
  it("denies viewers without settings codes", () => {
    const u = user({ roles: ["support_agent"], permissions: [] });
    expect(canViewRuntimeSettings(u)).toBe(false);
    expect(canEditRuntimeSettings(u)).toBe(false);
    expect(canEditRuntimeSecrets(u)).toBe(false);
    expect(canTestRuntimeIntegrations(u)).toBe(false);
    expect(canClearRuntimeOverrides(u)).toBe(false);
    expect(canViewRuntimeAudit(u)).toBe(false);
  });

  it("gates each action by permission code", () => {
    expect(
      canEditRuntimeSettings(
        user({ roles: [], permissions: ["admin.settings.edit_runtime"] }),
      ),
    ).toBe(true);
    expect(
      canEditRuntimeSecrets(
        user({ roles: [], permissions: ["admin.settings.edit_secrets"] }),
      ),
    ).toBe(true);
    expect(
      canTestRuntimeIntegrations(
        user({ roles: [], permissions: ["admin.settings.test_integrations"] }),
      ),
    ).toBe(true);
    expect(
      canClearRuntimeOverrides(
        user({ roles: [], permissions: ["admin.settings.clear_overrides"] }),
      ),
    ).toBe(true);
    expect(
      canViewRuntimeAudit(
        user({ roles: [], permissions: ["admin.settings.view_audit"] }),
      ),
    ).toBe(true);
    expect(
      canViewRuntimeSystemStatus(
        user({ roles: [], permissions: ["admin.settings.view"] }),
      ),
    ).toBe(true);
  });

  it("grants all capabilities to super_admin and admin.full_access", () => {
    const superAdmin = getRuntimeSettingsCapabilities(
      user({ roles: ["super_admin"], permissions: [] }),
    );
    const full = getRuntimeSettingsCapabilities(
      user({ roles: ["finance_admin"], permissions: ["admin.full_access"] }),
    );
    for (const caps of [superAdmin, full]) {
      expect(caps.view).toBe(true);
      expect(caps.editRuntime).toBe(true);
      expect(caps.editSecrets).toBe(true);
      expect(caps.testIntegrations).toBe(true);
      expect(caps.viewSystemStatus).toBe(true);
      expect(caps.clearOverrides).toBe(true);
      expect(caps.viewAudit).toBe(true);
    }
  });
});
