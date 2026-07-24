"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { AudienceMessageButton } from "@/components/messaging/AudienceMessageButton";
import { Alert, Badge, Button, Card, EmptyState } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchHostFollowers } from "@/lib/crm-api";
import type { AudienceMember } from "@/lib/types/crm";

export default function HostFollowersPage() {
  const [followers, setFollowers] = useState<AudienceMember[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchHostFollowers();
        if (active) setFollowers(rows);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load followers");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Audience"
        title="Followers"
        description="People who follow your host profile on Pàdéyá. Marketing messages require opt-in."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/audience">
              <Button variant="secondary">Audience dashboard</Button>
            </Link>
            <Link href="/host/announcements/new">
              <Button>Announce</Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Could not load followers">
            {error}
          </Alert>
        ) : null}

        {followers.length === 0 ? (
          <EmptyState
            title="No followers yet"
            description="Share your Legacy Page so fans can follow and stay close."
            action={
              <Link href="/host/legacy">
                <Button>Open Legacy Page</Button>
              </Link>
            }
          />
        ) : (
          <div className="space-y-4">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              {followers.length} follower{followers.length === 1 ? "" : "s"}
            </p>
            <div className="space-y-3">
              {followers.map((f) => (
                <Card key={f.user_id} className="flex flex-wrap items-center justify-between gap-3 !py-4">
                  <div>
                    <p className="font-bold text-foreground">{f.display_name}</p>
                    <p className="text-sm text-muted-foreground">{f.email}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {f.marketing_opt_in ? (
                      <Badge tone="accent">Marketing opt-in</Badge>
                    ) : (
                      <span className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                        Marketing off
                      </span>
                    )}
                    <AudienceMessageButton
                      fanUserId={f.user_id}
                      fanName={f.display_name}
                    />
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}
      </DashboardShell>
    </RequireHost>
  );
}
