"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Modal } from "@/components/ui";
import { trackHostMessageFanClicked } from "@/lib/analytics";
import { ApiError } from "@/lib/api";
import { createHostThread, hostCanMessageFan } from "@/lib/messaging-api";

export function AudienceMessageButton({
  fanUserId,
  fanName,
}: {
  fanUserId: string;
  fanName: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function openIfAllowed() {
    trackHostMessageFanClicked();
    setChecking(true);
    setError(null);
    try {
      const ok = await hostCanMessageFan(fanUserId);
      if (!ok) {
        setError("You can only message fans with a follow, ticket, or prior chat.");
        return;
      }
      setOpen(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unavailable");
    } finally {
      setChecking(false);
    }
  }

  return (
    <>
      <Button
        size="sm"
        variant="secondary"
        disabled={checking}
        onClick={() => void openIfAllowed()}
      >
        Message
      </Button>
      {error && !open ? (
        <span className="text-xs font-semibold text-danger">{error}</span>
      ) : null}
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={`Message ${fanName}`}
        description="No email or phone is shared. Stay on Pàdéyá."
      >
        <div className="space-y-3">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value.slice(0, 2000))}
            rows={4}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
          />
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
                  body: body.trim(),
                })
                  .then((t) => router.push(`/host/messages/${t.id}`))
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
