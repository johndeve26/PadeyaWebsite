"use client";

import { useState } from "react";

import { Alert, Button, Input, Modal } from "@/components/ui";
import { toLocalInput } from "@/components/events/studio/types";
import { ApiError } from "@/lib/api";
import { postponeEvent } from "@/lib/events-api";
import type { EventItem } from "@/lib/types/events";

type Props = {
  open: boolean;
  event: EventItem;
  onClose: () => void;
  onPostponed: (event: EventItem) => void;
};

export function HostEventPostponeModal({
  open,
  event,
  onClose,
  onPostponed,
}: Props) {
  const [start, setStart] = useState(() => toLocalInput(event.start_datetime));
  const [end, setEnd] = useState(() => toLocalInput(event.end_datetime));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function resetFromEvent(next: EventItem) {
    setStart(toLocalInput(next.start_datetime));
    setEnd(toLocalInput(next.end_datetime));
    setError(null);
  }

  async function onConfirm() {
    if (!start || !end) {
      setError("Choose both a new start and end.");
      return;
    }
    const startIso = new Date(start).toISOString();
    const endIso = new Date(end).toISOString();
    if (Number.isNaN(Date.parse(startIso)) || Number.isNaN(Date.parse(endIso))) {
      setError("Invalid date or time.");
      return;
    }
    if (new Date(endIso) <= new Date(startIso)) {
      setError("End must be after start.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const updated = await postponeEvent(event.id, {
        start_datetime: startIso,
        end_datetime: endIso,
      });
      resetFromEvent(updated);
      onPostponed(updated);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Postpone failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        if (!busy) {
          resetFromEvent(event);
          onClose();
        }
      }}
      title="Postpone event"
      description="Move the night to a new date. The listing stays live — no re-review. Door and check-in times shift with the start."
      footer={
        <>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => {
              resetFromEvent(event);
              onClose();
            }}
          >
            Keep dates
          </Button>
          <Button disabled={busy} onClick={() => void onConfirm()}>
            {busy ? "Saving…" : "Postpone"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error ? (
          <Alert tone="danger" title="Could not postpone">
            {error}
          </Alert>
        ) : null}
        <Input
          label="New start"
          type="datetime-local"
          value={start}
          onChange={(e) => setStart(e.target.value)}
          required
        />
        <Input
          label="New end"
          type="datetime-local"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
          required
        />
      </div>
    </Modal>
  );
}
