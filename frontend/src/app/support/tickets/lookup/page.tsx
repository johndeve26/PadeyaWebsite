"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import {
  Alert,
  Button,
  Card,
  Container,
  Input,
} from "@/components/ui";
import { brand } from "@/lib/brand";

export default function SupportTicketLookupPage() {
  const router = useRouter();
  const [ticketNumber, setTicketNumber] = useState("");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const number = ticketNumber.trim().toUpperCase();
    const mail = email.trim();
    if (number.length < 3) {
      setError("Enter your ticket number (e.g. SUP-…)." );
      return;
    }
    if (mail.length < 5 || !mail.includes("@")) {
      setError("Enter the email used when you submitted the ticket.");
      return;
    }
    const qs = new URLSearchParams({ email: mail });
    if (token.trim()) qs.set("token", token.trim());
    router.push(
      `/support/tickets/${encodeURIComponent(number)}?${qs.toString()}`,
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_color-mix(in_srgb,var(--primary)_12%,transparent),_transparent_50%)]"
      />
      <Container className="py-10 sm:py-14">
        <div className="mx-auto max-w-lg">
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-primary">
            {brand.name} Support
          </p>
          <h1 className="mt-2 text-3xl font-extrabold text-foreground sm:text-4xl">
            Track a ticket
          </h1>
          <p className="mt-2 text-muted-foreground">
            Use your ticket number and the email on the request.
          </p>
          <div className="mt-4">
            <Link href="/support">
              <Button size="sm" variant="ghost">
                ← Support Center
              </Button>
            </Link>
          </div>

          <Card className="mt-8 space-y-4 p-5 sm:p-6">
            {error ? (
              <Alert tone="danger" title="Check your details">
                {error}
              </Alert>
            ) : null}
            <form onSubmit={onSubmit} className="space-y-4">
              <Input
                label="Ticket number"
                value={ticketNumber}
                onChange={(e) => setTicketNumber(e.target.value)}
                placeholder="SUP-…"
                autoComplete="off"
                required
              />
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
              <Input
                label="Access token (optional)"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                hint="Included in confirmation emails when available."
                autoComplete="off"
              />
              <Button type="submit" size="lg" className="w-full sm:w-auto">
                View ticket
              </Button>
            </form>
          </Card>
        </div>
      </Container>
    </div>
  );
}
