export type TicketTransfer = {
  id: string;
  ticket_id: string;
  event_id: string;
  from_user_id: string;
  to_user_id: string | null;
  from_email: string;
  to_email: string;
  recipient_name?: string | null;
  note?: string | null;
  status: string;
  created_at: string;
  claim_path?: string | null;
};

export type TicketTransferActivity = TicketTransfer & {
  event_title?: string | null;
  ticket_public_code?: string | null;
  role: "sent" | "received";
  can_revoke: boolean;
  can_decline: boolean;
  can_resend_invite: boolean;
};

export type TableReservation = {
  id: string;
  event_id: string;
  ticket_type_id?: string | null;
  group_id?: string | null;
  primary_ticket_id?: string | null;
  table_label: string;
  seat_label?: string | null;
  capacity: number;
  status: string;
  assignment_note?: string | null;
  created_at: string;
  updated_at: string;
};

export type OfflineSyncResult = {
  batch_id: string;
  client_batch_id: string;
  status: string;
  accepted_count: number;
  conflict_count: number;
  invalid_count: number;
  results: {
    client_scan_id: string;
    sync_status: string;
    conflict_reason?: string | null;
    ticket?: { public_code?: string | null; status?: string | null } | null;
  }[];
};
