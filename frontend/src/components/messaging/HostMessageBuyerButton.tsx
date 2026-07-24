"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Modal } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasRole } from "@/lib/auth/permissions";
import {
  createHostThread,
  hostCanMessageFan,
} from "@/lib/messaging-api";

/**
 * Host CTA to message a buyer about a merch line — no email/phone in payloads.
 */
export function HostMessageBuyerButton({
  fanUserId,
  relatedEventId,
  relatedMerchOrderItemId,
  productName,
  label = "Message buyer",
  size = "sm",
  variant = "ghost",
}: {
  fanUserId: string;
  relatedEventId?: string;
  relatedMerchOrderItemId?: string;
  productName?: string;
  label?: string;
  size?: "sm" | "md" | "lg";
  variant?: "primary" | "secondary" | "ghost" | "outline-dark";
}) {
  const { user } = useAuth();
  const router = useRouter();
  const isHost = Boolean(user && userHasRole(user, "host", "host_staff"));
  const gateKey = isHost && fanUserId ? fanUserId : "";
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [loadedFor, setLoadedFor] = useState(gateKey);
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loadedFor !== gateKey) {
    setLoadedFor(gateKey);
    setAllowed(null);
  }

  useEffect(() => {
    if (!gateKey) return;
    let active = true;
    void hostCanMessageFan(gateKey)
      .then((ok) => {
        if (active) setAllowed(ok);
      })
      .catch(() => {
        if (active) setAllowed(false);
      });
    return () => {
      active = false;
    };
  }, [gateKey]);

  if (!gateKey || allowed !== true) return null;

  const defaultHint = productName
    ? `Hi — about your ${productName} pickup…`
    : "Hi — about your merch pickup…";

  return (
    <>
      <Button
        type="button"
        size={size}
        variant={variant}
        onClick={() => {
          setBody((prev) => prev || defaultHint);
          setOpen(true);
        }}
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
            className="w-full resize-none rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Write a message…"
          />
          {error ? (
            <p className="text-sm font-semibold text-danger">{error}</p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busy || !body.trim()}
              onClick={() => {
                setBusy(true);
                void createHostThread({
                  fan_user_id: fanUserId,
                  related_event_id: relatedEventId,
                  related_merch_order_item_id: relatedMerchOrderItemId,
                  subject: productName
                    ? `Merch: ${productName}`
                    : "Merch pickup",
                  body: body.trim(),
                })
                  .then((t) => {
                    setOpen(false);
                    router.push(`/host/messages/${t.id}`);
                  })
                  .catch((err) =>
                    setError(
                      err instanceof ApiError ? err.detail : "Could not send",
                    ),
                  )
                  .finally(() => setBusy(false));
              }}
            >
              Send
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
