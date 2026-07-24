"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  Input,
  PageToolbar,
  Select,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { createSupportCase } from "@/lib/support-api";

const CATEGORY_OPTIONS = [
  { value: "billing", label: "Billing" },
  { value: "tickets", label: "Tickets" },
  { value: "account", label: "Account" },
  { value: "events", label: "Events" },
  { value: "other", label: "Other" },
];

const PRIORITY_OPTIONS = [
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

export default function NewSupportCasePage() {
  const router = useRouter();
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState("other");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState("normal");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
      setError("Description must be at least 5 characters.");
      return;
    }

    setSubmitting(true);
    try {
      const created = await createSupportCase({
        subject: trimmedSubject,
        category,
        body: trimmedBody,
        priority,
      });
      router.push(`/support/cases/${created.id}`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not create support case",
      );
      setSubmitting(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title="New support case"
      description="Open a case on behalf of a user or for internal tracking. The first message is visible to the requester."
      actions={
        <Link href="/support/cases">
          <Button variant="secondary">All cases</Button>
        </Link>
      }
    >
      <PageToolbar>
        <Link href="/support/cases">
          <Button size="sm" variant="ghost">
            Back to cases
          </Button>
        </Link>
      </PageToolbar>

      <Alert tone="info" title="Before you submit">
        Include enough context for the next agent — order IDs, event slugs, and
        screenshots help. Urgent cases should only be used when access or payment
        is blocked.
      </Alert>

      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      <Card className="max-w-xl space-y-5 shadow-[var(--shadow-soft)]">
        <form className="space-y-4" onSubmit={onSubmit}>
          <Input
            label="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
            minLength={3}
            maxLength={200}
            placeholder="Short summary of the issue"
            hint="What the user sees in their case list."
          />

          <Select
            label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            hint="Routes the case to the right playbook."
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>

          <Select
            label="Priority"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            hint="Urgent is for blocked access or failed payments only."
          >
            {PRIORITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>

          <Textarea
            label="Description"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
            minLength={5}
            rows={6}
            placeholder="What happened, what you tried, and what the user needs."
            hint="This becomes the first public message on the case."
          />

          <Button type="submit" size="lg" disabled={submitting}>
            {submitting ? "Creating…" : "Create case"}
          </Button>
        </form>
      </Card>
    </DashboardShell>
  );
}
