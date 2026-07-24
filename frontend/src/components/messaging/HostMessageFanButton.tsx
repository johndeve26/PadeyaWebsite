"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button, Modal } from "@/components/ui";
import { trackHostMessageFanClicked } from "@/lib/analytics";
import { userHasRole } from "@/lib/auth/permissions";
import { formatSelfMessageError } from "@/lib/messaging-errors";
import {
  createHostThread,
  hostCanMessageFanUsername,
} from "@/lib/messaging-api";

/**
 * Host-only CTA on public/unlisted Fan Passport — never fan-to-fan.
 * Hidden when the fan’s settings (or lack of relationship) deny messaging.
 */
export function HostMessageFanButton({ fanUsername }: { fanUsername: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const isHost = Boolean(user && userHasRole(user, "host", "host_staff"));
  const gateKey = isHost && fanUsername ? fanUsername : "";
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [loadedFor, setLoadedFor] = useState(gateKey);
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset permission when host/fan context changes (render-time adjust).
  if (loadedFor !== gateKey) {
    setLoadedFor(gateKey);
    setAllowed(null);
  }

  useEffect(() => {
    if (!gateKey) return;
    let active = true;
    void hostCanMessageFanUsername(gateKey)
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

  // Hide until we know; never show a dead CTA when settings deny messaging
  if (!gateKey || allowed !== true) return null;

  return (
    <>
      <Button
        size="lg"
        variant="secondary"
        onClick={() => {
          trackHostMessageFanClicked();
          setOpen(true);
        }}
      >
        Message Fan
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Message Fan"
        description="Only message fans you already have a relationship with. Stay on Pàdéyá."
      >
        <div className="space-y-3">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value.slice(0, 2000))}
            rows={4}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Write a message…"
          />
          {error ? <p className="text-sm font-semibold text-danger">{error}</p> : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busy || !body.trim()}
              onClick={() => {
                setBusy(true);
                void createHostThread({
                  fan_username: fanUsername,
                  body: body.trim(),
                })
                  .then((t) => {
                    setOpen(false);
                    router.push(`/host/messages/${t.id}`);
                  })
                  .catch((err) => setError(formatSelfMessageError(err, "Could not send")))
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
