"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CheckInWorkspace } from "@/components/checkin/CheckInWorkspace";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { fetchEventById } from "@/lib/events-api";
import type { EventItem } from "@/lib/types/events";

export default function HostCheckInPage() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventItem | null>(null);

  useEffect(() => {
    void fetchEventById(params.id).then(setEvent).catch(() => setEvent(null));
  }, [params.id]);

  return (
    <RequireHost>
      <DashboardShell tone="soft" compact hideHeader>
        <CheckInWorkspace
          key={params.id}
          eventId={params.id}
          eventTitle={event?.title}
          variant="host"
        />
      </DashboardShell>
    </RequireHost>
  );
}
