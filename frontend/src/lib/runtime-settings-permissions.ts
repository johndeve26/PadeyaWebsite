import { userHasPermission, userHasRole } from "./auth/permissions";
import type { User } from "./auth/types";

export const RUNTIME_SETTINGS_PERMISSIONS = {
  view: "admin.settings.view",
  editRuntime: "admin.settings.edit_runtime",
  editSecrets: "admin.settings.edit_secrets",
  testIntegrations: "admin.settings.test_integrations",
  viewSystemStatus: "admin.settings.view_system_status",
  clearOverrides: "admin.settings.clear_overrides",
  viewAudit: "admin.settings.view_audit",
} as const;

function isSettingsSuperUser(user: User | null): boolean {
  if (!user) return false;
  return (
    userHasRole(user, "super_admin") ||
    userHasPermission(user, "admin.full_access")
  );
}

function has(user: User | null, code: string): boolean {
  if (!user) return false;
  if (isSettingsSuperUser(user)) return true;
  return userHasPermission(user, code);
}

export function canViewRuntimeSettings(user: User | null): boolean {
  return (
    has(user, RUNTIME_SETTINGS_PERMISSIONS.view) ||
    has(user, RUNTIME_SETTINGS_PERMISSIONS.viewSystemStatus) ||
    has(user, RUNTIME_SETTINGS_PERMISSIONS.editRuntime)
  );
}

export function canEditRuntimeSettings(user: User | null): boolean {
  return has(user, RUNTIME_SETTINGS_PERMISSIONS.editRuntime);
}

export function canEditRuntimeSecrets(user: User | null): boolean {
  return has(user, RUNTIME_SETTINGS_PERMISSIONS.editSecrets);
}

export function canTestRuntimeIntegrations(user: User | null): boolean {
  return has(user, RUNTIME_SETTINGS_PERMISSIONS.testIntegrations);
}

export function canViewRuntimeSystemStatus(user: User | null): boolean {
  return (
    has(user, RUNTIME_SETTINGS_PERMISSIONS.viewSystemStatus) ||
    has(user, RUNTIME_SETTINGS_PERMISSIONS.view)
  );
}

export function canClearRuntimeOverrides(user: User | null): boolean {
  return has(user, RUNTIME_SETTINGS_PERMISSIONS.clearOverrides);
}

export function canViewRuntimeAudit(user: User | null): boolean {
  return has(user, RUNTIME_SETTINGS_PERMISSIONS.viewAudit);
}

export type RuntimeSettingsCapabilities = {
  view: boolean;
  editRuntime: boolean;
  editSecrets: boolean;
  testIntegrations: boolean;
  viewSystemStatus: boolean;
  clearOverrides: boolean;
  viewAudit: boolean;
};

export function getRuntimeSettingsCapabilities(
  user: User | null,
): RuntimeSettingsCapabilities {
  return {
    view: canViewRuntimeSettings(user),
    editRuntime: canEditRuntimeSettings(user),
    editSecrets: canEditRuntimeSecrets(user),
    testIntegrations: canTestRuntimeIntegrations(user),
    viewSystemStatus: canViewRuntimeSystemStatus(user),
    clearOverrides: canClearRuntimeOverrides(user),
    viewAudit: canViewRuntimeAudit(user),
  };
}
