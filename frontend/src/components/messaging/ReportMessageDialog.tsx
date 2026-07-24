"use client";

import { useState } from "react";

import { Button, Input, Modal } from "@/components/ui";

export function ReportMessageDialog({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: string, details: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("harassment");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <Modal open={open} onClose={onClose} title="Report conversation">
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Reports are reviewed by Pàdéyá moderators. Full message content is not
          emailed.
        </p>
        <label className="block space-y-1 text-sm">
          <span className="font-semibold text-foreground">Reason</span>
          <select
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded-[var(--radius-md)] border border-border bg-background px-3 py-2"
          >
            <option value="harassment">Harassment</option>
            <option value="spam">Spam</option>
            <option value="scam">Scam / payment pressure</option>
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
              void onSubmit(reason, details)
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
