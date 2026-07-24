"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  Button,
  Input,
  Select,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  createPublicSupportTicket,
  createSupportTicket,
  fetchSupportMeta,
  supportTicketNumber,
} from "@/lib/support-api";
import { FALLBACK_SUPPORT_CATEGORIES } from "@/lib/support-ui";
import type {
  SupportCategoryOption,
  SupportDeflectionMeta,
} from "@/lib/types/support";
import { track } from "@/lib/analytics";

type SupportTicketFormProps = {
  /** fan | host | visitor (visitor uses public endpoint when logged out) */
  requesterContext?: "fan" | "host" | "visitor";
  relatedHostId?: string | null;
  initialCategory?: string | null;
  deflection?: SupportDeflectionMeta | null;
  /** Where to send authenticated users after create */
  successHrefForTicket?: (ticketId: string, ticketNumber: string) => string;
  /** Track page for visitors */
  visitorTrackHref?: (ticketNumber: string, email: string) => string;
  showContactFields?: boolean;
  className?: string;
};

export function SupportTicketForm({
  requesterContext = "fan",
  relatedHostId = null,
  initialCategory = null,
  deflection = null,
  successHrefForTicket,
  visitorTrackHref,
  showContactFields,
  className = "",
}: SupportTicketFormProps) {
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();

  const isLoggedIn = Boolean(user);
  const needsContact =
    showContactFields ?? (!isLoggedIn || requesterContext === "visitor");

  const [categories, setCategories] = useState<SupportCategoryOption[]>([
    ...FALLBACK_SUPPORT_CATEGORIES,
  ]);
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState(initialCategory || "other");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState("normal");
  const [name, setName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  /** Honeypot — leave empty */
  const [website, setWebsite] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync category from parent
    if (initialCategory) setCategory(initialCategory);
  }, [initialCategory]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const meta = await fetchSupportMeta();
        if (active && meta.categories?.length) {
          setCategories(meta.categories);
          setCategory((prev) =>
            meta.categories.some((c) => c.value === prev)
              ? prev
              : meta.categories[0]?.value ?? "other",
          );
        }
      } catch {
        // Keep fallbacks.
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Prefill contact fields when auth hydrates (visitor/public form).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate from auth
    if (user?.full_name) setName(user.full_name);
    if (user?.email) setEmail(user.email);
  }, [user?.full_name, user?.email]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const trimmedSubject = subject.trim();
    const trimmedBody = body.trim();
    if (trimmedSubject.length < 3) {
      setError("Subject must be at least 3 characters.");
      return;
    }
    if (trimmedBody.length < 5) {
      setError("Please describe the issue in a bit more detail.");
      return;
    }

    setSubmitting(true);
    try {
      if (isLoggedIn && requesterContext !== "visitor") {
        const created = await createSupportTicket({
          subject: trimmedSubject,
          category,
          body: trimmedBody,
          priority,
          requester_context: requesterContext,
          related_host_id: relatedHostId ?? undefined,
          deflection: deflection ?? undefined,
        });
        track("support_ticket_created", {
          metadata: {
            topic: category,
            after_help: String(Boolean(deflection?.help_suggestions_shown)),
          },
        });
        const number = supportTicketNumber(created);
        toast.push({
          tone: "success",
          title: "Ticket submitted",
          description: `Reference ${number}`,
        });
        const href =
          successHrefForTicket?.(created.id, number) ??
          `/dashboard/support/${created.id}`;
        router.push(href);
        return;
      }

      const trimmedName = name.trim();
      const trimmedEmail = email.trim();
      if (trimmedName.length < 2) {
        setError("Please enter your name.");
        setSubmitting(false);
        return;
      }
      if (trimmedEmail.length < 5 || !trimmedEmail.includes("@")) {
        setError("Please enter a valid email.");
        setSubmitting(false);
        return;
      }

      const created = await createPublicSupportTicket({
        subject: trimmedSubject,
        category,
        body: trimmedBody,
        priority,
        requester_name: trimmedName,
        requester_email: trimmedEmail,
        website,
        deflection: deflection ?? undefined,
      });
      track("support_ticket_created", {
        metadata: {
          topic: category,
          after_help: String(Boolean(deflection?.help_suggestions_shown)),
        },
      });
      const number = supportTicketNumber(created);
      toast.push({
        tone: "success",
        title: "Ticket submitted",
        description: `Save reference ${number} to track updates.`,
      });
      const href =
        visitorTrackHref?.(number, trimmedEmail) ??
        `/support/tickets/${encodeURIComponent(number)}?email=${encodeURIComponent(trimmedEmail)}${
          created.public_token
            ? `&token=${encodeURIComponent(created.public_token)}`
            : ""
        }`;
      router.push(href);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not submit your ticket",
      );
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className={`relative space-y-4 ${className}`}>
      {error ? (
        <Alert tone="danger" title="Could not submit">
          {error}
        </Alert>
      ) : null}

      {needsContact ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
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
        </div>
      ) : null}

      {/* Honeypot — hidden from users */}
      <div
        className="absolute -left-[9999px] h-0 w-0 overflow-hidden opacity-0"
        aria-hidden="true"
      >
        <label htmlFor="support-website">Website</label>
        <input
          id="support-website"
          name="website"
          tabIndex={-1}
          autoComplete="off"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
        />
      </div>

      <Input
        label="Subject"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        placeholder="Short summary of the issue"
        required
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {categories.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          label="Priority"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          <option value="low">Low</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </Select>
      </div>

      <Textarea
        label="How can we help?"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={6}
        placeholder="Include order numbers, event names, or steps you’ve already tried…"
        required
      />

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={submitting} size="lg">
          {submitting ? "Submitting…" : "Submit ticket"}
        </Button>
        <Link
          href="/support"
          className="text-sm font-semibold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Back to Support Center
        </Link>
      </div>
    </form>
  );
}
