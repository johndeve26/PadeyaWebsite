import { permanentRedirect } from "next/navigation";

export const revalidate = 90;

/**
 * Map-first entry — redirects to the indexable /events marketplace
 * with client-side map view.
 */
export default function EventsMapPage() {
  permanentRedirect("/events?view=map");
}
