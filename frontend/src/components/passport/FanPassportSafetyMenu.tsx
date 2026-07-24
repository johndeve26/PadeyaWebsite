"use client";

import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Button,
  Modal,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  blockFanConnect,
  reportFanConnect,
} from "@/lib/fan-connect-api";
import {
  formatSelfBlockError,
  formatSelfReportError,
} from "@/lib/messaging-errors";
import { fanPageCtas, isOwnFanPassport } from "@/lib/own-fan-ctas";

type FanCtas = ReturnType<typeof fanPageCtas>;

/**
 * Report / Block controls for public Fan Passport surfaces.
 * Never rendered on own Passport or own directory card.
 */
export function FanPassportSafetyMenu({
  username,
  passportOwnerUserId,
  isOwnPassport = false,
  ctas,
  compact = false,
}: {
  username: string;
  passportOwnerUserId?: string | null;
  isOwnPassport?: boolean;
  ctas?: FanCtas;
  compact?: boolean;
}) {
  const { user } = useAuth();
  const toast = useToast();
  const [reportOpen, setReportOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const own =
    isOwnPassport ||
    isOwnFanPassport(user?.id, passportOwnerUserId);
  const resolved =
    ctas ?? fanPageCtas(own ? "own_passport" : "visitor");

  if (
    own ||
    !user ||
    (!resolved.showReport && !resolved.showBlock)
  ) {
    return null;
  }

  const size = compact ? "sm" : "md";

  return (
    <>
      <div className={compact ? "flex w-full gap-2" : "flex flex-wrap gap-2"}>
        {resolved.showBlock ? (
          <Button
            size={size}
            variant="secondary"
            className={compact ? "min-w-0 flex-1" : undefined}
            disabled={busy}
            onClick={() => {
              setBusy(true);
              void blockFanConnect({ username })
                .then(() => {
                  toast.push({ tone: "success", title: "Blocked" });
                })
                .catch((err) => {
                  toast.push({
                    tone: "danger",
                    title: "Could not block",
                    description: formatSelfBlockError(err),
                  });
                })
                .finally(() => setBusy(false));
            }}
          >
            Block
          </Button>
        ) : null}
        {resolved.showReport ? (
          <Button
            size={size}
            variant="secondary"
            className={compact ? "min-w-0 flex-1" : undefined}
            disabled={busy}
            onClick={() => {
              setReportOpen(true);
              setReason("");
              setDetails("");
              setError(null);
            }}
          >
            Report
          </Button>
        ) : null}
      </div>

      <Modal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        title="Report fan"
        description="Tell us what’s wrong. Reports stay private to Pàdéyá moderation."
      >
        <div className="space-y-3">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value.slice(0, 120))}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Reason (required)"
          />
          <textarea
            value={details}
            onChange={(e) => setDetails(e.target.value.slice(0, 2000))}
            rows={3}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2 text-sm"
            placeholder="Optional details"
          />
          {error ? (
            <p className="text-sm font-semibold text-danger">{error}</p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setReportOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busy || reason.trim().length < 3}
              onClick={() => {
                setBusy(true);
                setError(null);
                void reportFanConnect({
                  username,
                  reason: reason.trim(),
                  details: details.trim() || undefined,
                })
                  .then(() => {
                    setReportOpen(false);
                    toast.push({
                      tone: "success",
                      title: "Report submitted",
                    });
                  })
                  .catch((err) => {
                    setError(
                      formatSelfReportError(
                        err,
                        err instanceof ApiError
                          ? err.detail
                          : "Could not submit report.",
                      ),
                    );
                  })
                  .finally(() => setBusy(false));
              }}
            >
              Submit report
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
