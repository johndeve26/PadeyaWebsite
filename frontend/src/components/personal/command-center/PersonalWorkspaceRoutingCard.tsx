"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { useOptionalSponsorWorkspace } from "@/components/sponsor/SponsorWorkspaceProvider";
import { Button, Card } from "@/components/ui";
import { isHostSponsorDeskOnlyMember } from "@/lib/host-access";
import { SPONSOR_WORKSPACE_SWITCHER_LABEL } from "@/lib/nav/sponsor-nav";

/**
 * Routes users off Personal when their job lives in Host or Sponsor brand shells.
 * Demo: sponsor-observer@demo.padeye.test — host team, not sponsor brand owner.
 */
export function PersonalWorkspaceRoutingCard() {
  const { workspaces, active, loading: hostLoading } = useHostWorkspace();
  const sponsorCtx = useOptionalSponsorWorkspace();
  const sponsorWorkspaces = sponsorCtx?.workspaces ?? [];
  const sponsorLoading = sponsorCtx?.loading ?? false;

  const hostSponsorDesk = useMemo(() => {
    const candidates = active ? [active, ...workspaces] : workspaces;
    for (const row of candidates) {
      if (isHostSponsorDeskOnlyMember(row)) return row;
    }
    return null;
  }, [active, workspaces]);

  if (hostLoading || sponsorLoading) return null;

  if (sponsorWorkspaces.length > 0) {
    const primary =
      sponsorWorkspaces.find((w) => w.is_owner) ?? sponsorWorkspaces[0]!;
    return (
      <Card className="min-w-0 space-y-3 border-accent/35 bg-accent/5 p-4 sm:p-5">
        <div className="min-w-0 space-y-1.5">
          <p className="text-xs font-bold uppercase tracking-wide text-accent">
            {SPONSOR_WORKSPACE_SWITCHER_LABEL}
          </p>
          <h2 className="text-base font-bold text-foreground">
            Open {primary.display_name}
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Personal is for tickets, Passport, and fan tools. Campaigns, deals,
            and sponsor profile live in your sponsor brand workspace — use the
            workspace switcher in the sidebar or open it below.
          </p>
        </div>
        <Link href="/sponsor">
          <Button size="sm">Open sponsor workspace</Button>
        </Link>
      </Card>
    );
  }

  if (hostSponsorDesk) {
    const role = hostSponsorDesk.role_label?.trim() || "Sponsor desk";
    return (
      <Card className="min-w-0 space-y-3 border-border bg-surface-muted/80 p-4 sm:p-5">
        <div className="min-w-0 space-y-1.5">
          <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Host workspace · Sponsorship
          </p>
          <h2 className="text-base font-bold text-foreground">
            Not a sponsor brand account
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground">
            You have read-only sponsorship access on{" "}
            <span className="font-semibold text-foreground">
              {hostSponsorDesk.display_name}
            </span>{" "}
            ({role}) — that is a{" "}
            <span className="font-semibold text-foreground">host</span> desk, not
            a NeonPalm-style sponsor company workspace. Personal will not show
            sponsor campaigns here.
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            In the sidebar workspace switcher, choose{" "}
            <span className="font-semibold text-foreground">
              Host: {hostSponsorDesk.display_name} · {role}
            </span>
            , or use{" "}
            <Link
              href="/dashboard/team"
              className="font-semibold text-accent underline-offset-2 hover:underline"
            >
              Workspaces
            </Link>
            .
          </p>
        </div>
        <Link href="/host/sponsorships">
          <Button size="sm">Open host sponsor desk</Button>
        </Link>
      </Card>
    );
  }

  return null;
}
