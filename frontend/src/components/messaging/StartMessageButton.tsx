"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Modal } from "@/components/ui";
import { useHostAffiliation } from "@/hooks/useHostAffiliation";
import { trackMessageCtaClicked } from "@/lib/analytics";
import { ApiError } from "@/lib/api";
import { createFanThread } from "@/lib/messaging-api";
import {
  formatSelfMessageError,
  SELF_MESSAGE_DETAIL,
} from "@/lib/messaging-errors";

const OWN_HOST_MESSAGE =
  "You can’t message your own host workspace from your Personal account.";

export function StartMessageButton({
  hostId,
  hostUsername,
  relatedEventId,
  relatedMerchOrderItemId,
  productName,
  label = "Message Host",
  variant = "secondary",
  size = "md",
  returnPath,
  defaultBody,
  id,
  className,
}: {
  hostId?: string;
  hostUsername?: string;
  relatedEventId?: string;
  relatedMerchOrderItemId?: string;
  productName?: string;
  label?: string;
  variant?: "primary" | "secondary" | "ghost" | "outline-dark";
  size?: "sm" | "md" | "lg";
  returnPath?: string;
  defaultBody?: string;
  id?: string;
  className?: string;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { affiliated: hideForOwnHost } = useHostAffiliation({
    hostId,
    hostSlug: hostUsername,
  });

  if (hideForOwnHost) {
    // Own-host public pages replace this with Host Inbox / workspace CTAs.
    // Keep hidden everywhere else so Personal surfaces never offer self-message.
    return null;
  }

  function onClick() {
    trackMessageCtaClicked({
      context: relatedMerchOrderItemId
        ? "merch"
        : relatedEventId
          ? "event_detail"
          : "legacy",
      hostUsername: hostUsername || undefined,
    });
    if (!user) {
      const fallback =
        returnPath ||
        (hostUsername ? `/@${hostUsername}` : null) ||
        (typeof window !== "undefined" ? window.location.pathname : "/dashboard/messages");
      router.push(`/login?next=${encodeURIComponent(fallback)}`);
      return;
    }
    const hint =
      defaultBody ||
      (productName
        ? `Hi — I have a question about my ${productName}.`
        : relatedMerchOrderItemId
          ? "Hi — I have a question about my merch pickup."
          : "");
    if (hint && !body.trim()) setBody(hint);
    setOpen(true);
  }

  async function send() {
    const text = body.trim();
    if (!text) return;
    setBusy(true);
    setError(null);
    try {
      const thread = await createFanThread({
        host_id: hostId,
        host_username: hostUsername,
        related_event_id: relatedEventId,
        related_merch_order_item_id: relatedMerchOrderItemId,
        body: text,
        subject: relatedMerchOrderItemId
          ? productName
            ? `Merch: ${productName}`
            : "Merch question"
          : relatedEventId
            ? "Event question"
            : undefined,
      });
      setOpen(false);
      router.push(`/dashboard/messages/${thread.id}`);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not start conversation";
      const lower = detail.toLowerCase();
      if (
        lower.includes("message yourself") ||
        lower === "invalid pair."
      ) {
        setError(SELF_MESSAGE_DETAIL);
      } else if (lower.includes("own host workspace")) {
        setError(OWN_HOST_MESSAGE);
      } else if (lower.includes("blocked")) {
        setError("This conversation is blocked. Messages cannot be sent.");
      } else if (lower.includes("cannot message")) {
        setError(
          "You can’t message this host right now. Follow them, grab a ticket, or send an event inquiry when available.",
        );
      } else {
        setError(formatSelfMessageError(err, detail));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button
        id={id}
        type="button"
        variant={variant}
        size={size}
        className={className}
        onClick={onClick}
      >
        {label}
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={label}
        description="Messages stay on Pàdéyá. Do not share phone numbers or payment details."
      >
        <div className="space-y-3">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value.slice(0, 2000))}
            rows={4}
            placeholder="Write your message…"
            className="w-full resize-none rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
          />
          {error ? <p className="text-sm font-semibold text-danger">{error}</p> : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button disabled={busy || !body.trim()} onClick={() => void send()}>
              Send
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
