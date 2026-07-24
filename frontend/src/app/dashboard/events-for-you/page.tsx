import Link from "next/link";

import { EventRecommendationsSection } from "@/components/events/EventRecommendationsSection";
import { Button, Container } from "@/components/ui";

export const metadata = {
  title: "Events for you | Pàdéyá",
  description: "Personalized event recommendations based on your tickets, follows, and city.",
};

export default function DashboardEventsForYouPage() {
  return (
    <Container className="space-y-6 py-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-extrabold tracking-tight">Events for you</h1>
        <p className="text-sm text-muted-foreground">
          Rules-based picks from your tickets, hosts you follow, and city — never AI-ranked.
        </p>
      </div>
      <EventRecommendationsSection variant="page" limit={12} surface="dashboard_events_for_you" />
      <Link href="/events">
        <Button variant="secondary">Browse all events</Button>
      </Link>
    </Container>
  );
}
