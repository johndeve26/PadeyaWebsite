/**
 * Own-message delivery / read labels from real server + client state.
 * Do not invent Read/Delivered without status or peer_read_at evidence.
 */

export type MessageStatusInput = {
  isMine: boolean;
  status: string;
  createdAt?: string | null;
  editedAt?: string | null;
  /** Counterpart thread-level read cursor (real receipt). */
  peerReadAt?: string | null;
  /** Client-only send failure (optimistic local row). */
  clientFailed?: boolean;
};

function isAtOrBefore(
  cursor: string | null | undefined,
  createdAt: string | null | undefined,
): boolean {
  if (!cursor || !createdAt) return false;
  const c = new Date(cursor).getTime();
  const m = new Date(createdAt).getTime();
  if (Number.isNaN(c) || Number.isNaN(m)) return false;
  return c >= m;
}

/**
 * Delivery label for own messages only.
 * Priority: Failed > Read > Delivered > Sent.
 */
export function formatOwnDeliveryStatus(input: MessageStatusInput): string | null {
  if (!input.isMine) return null;
  if (input.clientFailed || input.status === "failed") return "Failed";
  if (isAtOrBefore(input.peerReadAt, input.createdAt)) return "Read";
  if (input.status === "delivered") return "Delivered";
  // Hidden/deleted moderation states — no delivery chrome.
  if (input.status === "hidden" || input.status === "deleted") return null;
  // Persisted sends start as `sent`.
  return "Sent";
}

/** Metadata chips after the clock (Edited for any message; delivery for own only). */
export function ownMessageStatusBits(input: MessageStatusInput): string[] {
  const bits: string[] = [];
  if (input.editedAt) bits.push("Edited");
  const delivery = formatOwnDeliveryStatus(input);
  if (delivery) bits.push(delivery);
  return bits;
}
