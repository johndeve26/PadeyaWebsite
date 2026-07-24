"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { useOptionalSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import {
  ADMIN_PANEL_SWITCHER_LABEL,
  SUPPORT_DESK_SWITCHER_LABEL,
  canAccessAdminPanel,
  canAccessSupportDesk,
} from "@/lib/auth/workspace-access";
import {
  hostHomePathForWorkspace,
  isHostSponsorDeskOnlyMember,
  PERSONAL_WORKSPACE_SWITCHER_LABEL,
  workspaceManagementHint,
  workspaceSwitcherOptionLabel,
} from "@/lib/host-access";
import {
  syncWorkspaceModeFromPath,
  writeWorkspaceMode,
} from "@/lib/host-workspace";
import { SPONSOR_WORKSPACE_SWITCHER_LABEL } from "@/lib/nav/sponsor-nav";
import { syncSponsorModeFromPath } from "@/lib/sponsor-workspace";

const PERSONAL = "personal";
const ADMIN = "admin";
const SUPPORT = "support";
const SPONSOR_PREFIX = "sponsor:";

function isSupportDeskPath(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  return (
    pathname === "/support/desk" ||
    pathname.startsWith("/support/desk/") ||
    pathname === "/support/cases" ||
    pathname.startsWith("/support/cases/") ||
    pathname === "/support/refunds" ||
    pathname.startsWith("/support/refunds/")
  );
}

export function WorkspaceSwitcher({
  className = "",
}: {
  className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isImpersonating } = useAuth();
  const { workspaces, active, setActiveHostId, loading: hostLoading } =
    useHostWorkspace();
  const sponsorCtx = useOptionalSponsorWorkspace();
  const sponsorWorkspaces = sponsorCtx?.workspaces ?? [];
  const activeSponsor = sponsorCtx?.active ?? null;
  const setActiveSponsorId = sponsorCtx?.setActiveSponsorId;
  const sponsorLoading = sponsorCtx?.loading ?? false;

  const showAdmin = canAccessAdminPanel(user, isImpersonating);
  const showSupport = canAccessSupportDesk(user, isImpersonating);
  const loading = hostLoading || sponsorLoading;

  const hostSponsorDeskOnly =
    workspaces.length > 0 &&
    workspaces.every(isHostSponsorDeskOnlyMember);

  useEffect(() => {
    syncWorkspaceModeFromPath(pathname);
    syncSponsorModeFromPath(pathname);
  }, [pathname]);

  const onHostSurface = Boolean(
    pathname === "/host" || pathname?.startsWith("/host/"),
  );
  const onSponsorSurface = Boolean(
    pathname === "/sponsor" || pathname?.startsWith("/sponsor/"),
  );
  const onAdminSurface = Boolean(
    pathname === "/admin" || pathname?.startsWith("/admin/"),
  );
  const onSupportDeskSurface = isSupportDeskPath(pathname);

  const value = useMemo(() => {
    if (onAdminSurface && showAdmin) return ADMIN;
    if (onSupportDeskSurface && showSupport) return SUPPORT;
    if (onSponsorSurface && activeSponsor) {
      return `${SPONSOR_PREFIX}${activeSponsor.sponsor_id}`;
    }
    if (onHostSurface && active) {
      if (!workspaces.some((w) => w.host_id === active.host_id)) return PERSONAL;
      return active.host_id;
    }
    return PERSONAL;
  }, [
    active,
    activeSponsor,
    onAdminSurface,
    onHostSurface,
    onSponsorSurface,
    onSupportDeskSurface,
    showAdmin,
    showSupport,
    workspaces,
  ]);

  const shellClass = `flex min-w-0 w-full max-w-full flex-col gap-1 text-xs font-semibold text-muted-foreground ${className}`;

  if (loading) {
    return (
      <div className={shellClass}>
        <span className="uppercase tracking-wide">Workspace</span>
        <div
          className="h-9 animate-pulse rounded-md border border-border bg-muted"
          aria-hidden
        />
      </div>
    );
  }

  const hint = (() => {
    const hasOtherWorkspaces =
      workspaces.length > 0 ||
      sponsorWorkspaces.length > 0 ||
      showAdmin ||
      showSupport;
    if (onAdminSurface && showAdmin) {
      return workspaceManagementHint({ surface: "admin" });
    }
    if (onSupportDeskSurface && showSupport) {
      return workspaceManagementHint({ surface: "support" });
    }
    if (onSponsorSurface && activeSponsor) {
      return `Managing ${activeSponsor.display_name} sponsor workspace.`;
    }
    if (onHostSurface && active) {
      return workspaceManagementHint({
        surface: "host",
        hostDisplayName: active.display_name,
      });
    }
    if (hostSponsorDeskOnly && active) {
      return `You're on your personal account. Switch to Host: ${active.display_name} · ${active.role_label || "Sponsor desk"} for read-only host sponsorship tools — this is not a sponsor brand workspace.`;
    }
    return workspaceManagementHint({
      surface: "personal",
      hasOtherWorkspaces,
    });
  })();

  return (
    <div className={shellClass}>
      <label className="flex min-w-0 w-full flex-col gap-1">
        <span className="uppercase tracking-wide">Workspace</span>
        <select
          className="h-9 max-w-full truncate rounded-md border border-border bg-card px-2 text-sm font-semibold text-foreground"
          value={value}
          aria-label="Switch workspace"
          aria-describedby="workspace-switcher-hint"
          onChange={(e) => {
            const next = e.target.value;
            if (next === PERSONAL) {
              writeWorkspaceMode("personal");
              router.push("/dashboard");
              return;
            }
            if (next === ADMIN) {
              writeWorkspaceMode("admin");
              router.push("/admin");
              return;
            }
            if (next === SUPPORT) {
              writeWorkspaceMode("support");
              router.push("/support/desk");
              return;
            }
            if (next.startsWith(SPONSOR_PREFIX)) {
              const id = next.slice(SPONSOR_PREFIX.length);
              const match = sponsorWorkspaces.find((w) => w.sponsor_id === id);
              if (!match || !setActiveSponsorId) {
                writeWorkspaceMode("personal");
                router.push("/dashboard");
                return;
              }
              setActiveSponsorId(match.sponsor_id);
              writeWorkspaceMode("sponsor");
              router.push("/sponsor");
              return;
            }
            const match = workspaces.find((w) => w.host_id === next);
            if (!match) {
              writeWorkspaceMode("personal");
              router.push("/dashboard");
              return;
            }
            setActiveHostId(match.host_id);
            writeWorkspaceMode("host");
            router.push(hostHomePathForWorkspace(match));
          }}
        >
          <option value={PERSONAL}>{PERSONAL_WORKSPACE_SWITCHER_LABEL}</option>
          {showAdmin ? (
            <option value={ADMIN}>{ADMIN_PANEL_SWITCHER_LABEL}</option>
          ) : null}
          {showSupport ? (
            <option value={SUPPORT}>{SUPPORT_DESK_SWITCHER_LABEL}</option>
          ) : null}
          {sponsorWorkspaces.length > 0 ? (
            <optgroup label="Sponsor workspaces">
              {sponsorWorkspaces.map((w) => (
                <option
                  key={w.sponsor_id}
                  value={`${SPONSOR_PREFIX}${w.sponsor_id}`}
                >
                  {w.display_name} · {SPONSOR_WORKSPACE_SWITCHER_LABEL}
                </option>
              ))}
            </optgroup>
          ) : null}
          {workspaces.length > 0 ? (
            <optgroup label="Host workspaces">
              {workspaces.map((w) => (
                <option key={w.host_id} value={w.host_id}>
                  {workspaceSwitcherOptionLabel(w)}
                </option>
              ))}
            </optgroup>
          ) : null}
        </select>
      </label>
      <p
        id="workspace-switcher-hint"
        className="px-0.5 text-[11px] font-medium leading-snug text-foreground/85"
      >
        {hint}
      </p>
      {workspaces.length === 0 ? (
        <Link
          href="/host/onboarding"
          className="px-0.5 text-xs font-semibold text-accent underline-offset-2 hover:underline"
        >
          Become a host
        </Link>
      ) : null}
      {hostSponsorDeskOnly && active ? (
        <Link
          href="/host/sponsorships"
          className="px-0.5 text-xs font-semibold text-accent underline-offset-2 hover:underline"
        >
          Open host sponsor desk
        </Link>
      ) : null}
      {sponsorWorkspaces.length === 0 && !hostSponsorDeskOnly ? (
        <Link
          href="/sponsor/create"
          className="px-0.5 text-xs font-semibold text-accent underline-offset-2 hover:underline"
        >
          Create sponsor profile
        </Link>
      ) : null}
    </div>
  );
}

/** @deprecated Use WorkspaceSwitcher */
export function HostWorkspaceSwitcher() {
  return <WorkspaceSwitcher />;
}
