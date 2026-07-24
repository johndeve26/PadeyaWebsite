"use client";

import Link from "next/link";

import { Button, Container } from "@/components/ui";
import { PERSONAL_WORKSPACE_SWITCHER_LABEL } from "@/lib/host-access";

export function HostPermissionDenied({
  backHref = "/host",
}: {
  backHref?: string;
}) {
  return (
    <main className="bg-background py-16 sm:py-20">
      <Container
        width="narrow"
        className="space-y-4 rounded-[var(--radius-lg)] border border-border bg-card p-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated"
      >
        <h1 className="text-2xl font-extrabold tracking-tight text-heading">
          You do not have access to this area.
        </h1>
        <p className="text-base leading-relaxed text-muted-foreground">
          Ask the host owner to update your team permissions.
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          <Link href={backHref}>
            <Button variant="secondary">Back to workspace</Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="ghost">{PERSONAL_WORKSPACE_SWITCHER_LABEL}</Button>
          </Link>
        </div>
      </Container>
    </main>
  );
}
