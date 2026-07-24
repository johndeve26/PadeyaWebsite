"use client";

import Link from "next/link";

import { Button, EmptyState } from "@/components/ui";

type Props = {
  eventSlug: string;
  diagnostics?: string[];
  isDev?: boolean;
};

export function MerchEmptyState({ eventSlug, diagnostics, isDev }: Props) {
  return (
    <EmptyState
      title="No merch available yet"
      description="When this host adds official event merch, it will appear here."
      action={
        <div className="flex flex-col items-center gap-3">
          <Link href={`/events/${eventSlug}`}>
            <Button variant="secondary">Back to event</Button>
          </Link>
          {isDev && diagnostics && diagnostics.length > 0 ? (
            <ul className="max-w-md space-y-1 text-left text-xs text-muted-foreground">
              {diagnostics.map((line) => (
                <li key={line}>· {line}</li>
              ))}
            </ul>
          ) : null}
        </div>
      }
    />
  );
}
