import { permanentRedirect } from "next/navigation";

export const revalidate = 90;

/**
 * Calendar-first entry — redirects to the indexable /events marketplace
 * with client-side calendar view (avoids crawlable month URL sprawl).
 */
export default function EventsCalendarPage() {
  permanentRedirect("/events?view=calendar");
}
