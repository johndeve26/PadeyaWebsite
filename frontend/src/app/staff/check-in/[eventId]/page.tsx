"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RestrictedActionNotice } from "@/components/account/RestrictedActionNotice";
import { CheckInWorkspace } from "@/components/checkin/CheckInWorkspace";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { SkeletonLoader } from "@/components/ui";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { fetchEventById } from "@/lib/events-api";

export default function StaffCheckInPage() {
  const params = useParams<{ eventId: string }>();
  const { has } = useUserRestrictions();
  const blocked = has("cannot_scan_tickets");
  const [eventTitle, setEventTitle] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void fetchEventById(params.eventId)
      .then((event) => {
        if (active) setEventTitle(event.title);
      })
      .catch(() => {
        // Title is optional — scanner still works with event id only.
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.eventId]);

  return (
    <DashboardShell compact tone="soft" hideHeader>
      {blocked ? (
        <RestrictedActionNotice />
      ) : (
        <>
          {loading && !eventTitle ? <SkeletonLoader lines={2} /> : null}
          <CheckInWorkspace
            key={params.eventId}
            eventId={params.eventId}
            eventTitle={eventTitle ?? undefined}
            variant="staff"
          />
        </>
      )}
    </DashboardShell>
  );
}
