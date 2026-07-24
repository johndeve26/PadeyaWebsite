"use client";

import { useState } from "react";

import { Button, Input, Modal } from "@/components/ui";

const REASON_LABELS: Record<string, string> = {
  spam: "Spam or misleading listing",
  off_platform_payment: "Off-platform payment or external link",
  unsafe_content: "Unsafe or banned product content",
  scam: "Scam or fraudulent listing",
  other: "Other concern",
};

export function ReportMerchDialog({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: string, details: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("spam");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <Modal open={open} onClose={onClose} title="Report merch listing">
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Reports go to Pàdéyá moderators. Do not include payment details or
          private contact information in your report.
        </p>
        <label className="block space-y-1 text-sm">
          <span className="font-semibold text-foreground">Reason</span>
          <select
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2"
          >
            <option value="spam">Spam or misleading</option>
            <option value="off_platform_payment">Off-platform payment link</option>
            <option value="unsafe_content">Unsafe or banned product</option>
            <option value="scam">Scam or fraud</option>
            <option value="other">Other</option>
          </select>
        </label>
        <Input
          label="Details"
          value={details}
          onChange={(e) => setDetails(e.target.value)}
          placeholder="Optional context"
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            variant="danger"
            disabled={busy}
            onClick={() => {
              setBusy(true);
              const label = REASON_LABELS[reason] ?? REASON_LABELS.other;
              const reasonText = details.trim()
                ? `${label}: ${details.trim()}`
                : label;
              void onSubmit(reasonText, details.trim())
                .then(onClose)
                .finally(() => setBusy(false));
            }}
          >
            Submit report
          </Button>
        </div>
      </div>
    </Modal>
  );
}
