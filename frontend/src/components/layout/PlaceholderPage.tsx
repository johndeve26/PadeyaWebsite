import Link from "next/link";

import { Badge, Button, Container, SectionHeader } from "@/components/ui";

export type PlaceholderPageProps = {
  title: string;
  description: string;
  eyebrow?: string;
};

export function PlaceholderPage({
  title,
  description,
  eyebrow = "Coming in a later phase",
}: PlaceholderPageProps) {
  return (
    <main className="bg-background py-20">
      <Container width="narrow" className="space-y-8 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated sm:p-8">
        <Badge tone="accent">{eyebrow}</Badge>
        <SectionHeader title={title} description={description} />
        <div className="flex flex-wrap gap-3">
          <Link href="/">
            <Button variant="dark">Back home</Button>
          </Link>
          <Link href="/events">
            <Button variant="secondary">Browse events</Button>
          </Link>
        </div>
      </Container>
    </main>
  );
}
