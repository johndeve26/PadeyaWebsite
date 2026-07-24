"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button, Input } from "@/components/ui";

/** Hero search that navigates to /help?q=… */
export function HelpSearch({
  initialQuery = "",
  actionHref = "/help",
}: {
  initialQuery?: string;
  actionHref?: string;
}) {
  const router = useRouter();
  const [q, setQ] = useState(initialQuery);
  const [pending, startTransition] = useTransition();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = q.trim();
    const href = trimmed
      ? `${actionHref}?q=${encodeURIComponent(trimmed)}`
      : actionHref;
    startTransition(() => {
      router.push(href);
    });
  }

  return (
    <form
      onSubmit={submit}
      className="flex w-full flex-col gap-3 sm:flex-row sm:items-center"
      role="search"
    >
      <label className="sr-only" htmlFor="help-search">
        Search help articles
      </label>
      <Input
        id="help-search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search tickets, refunds, hosting, Fan Passport, checkout…"
        className="h-12 flex-1 border-border bg-card text-base shadow-[var(--shadow-soft)]"
        autoComplete="off"
      />
      <Button type="submit" size="lg" disabled={pending} className="h-12 shrink-0 sm:px-8">
        {pending ? "Searching…" : "Search"}
      </Button>
    </form>
  );
}
