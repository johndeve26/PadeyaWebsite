import type { EventItem } from "@/lib/types/events";
import type { EventListMetrics } from "@/lib/host-events-list";

export type EventRowActions = {
  canView: boolean;
  canEdit: boolean;
  canTickets: boolean;
  canScanner: boolean;
  canMerch: boolean;
  canAmbassadors: boolean;
  canAnalytics: boolean;
  showFinance: boolean;
  showOpsMetrics: boolean;
  scannerOnly: boolean;
  merchOnly: boolean;
  deskOnly: boolean;
};

export type HostEventsViewProps = {
  events: EventItem[];
  actions: EventRowActions;
  metrics: Record<string, EventListMetrics>;
  metricsLoading: boolean;
  onView: (event: EventItem) => void;
};

export const VIEW_MODE_STORAGE_KEY = "padeya:host-events:view-mode";
