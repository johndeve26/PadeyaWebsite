import { apiRequest } from "@/lib/api";

export type ScanResult = {
  outcome: "success" | "duplicate" | "invalid" | "valid" | string;
  message: string;
  ticket: {
    ticket_id: string | null;
    public_code: string | null;
    status: string | null;
    holder_name: string | null;
    /** Always null for desk scanners. */
    holder_email: string | null;
    ticket_type_name: string | null;
    checked_in_at: string | null;
  } | null;
  check_in_id: string | null;
  checked_in_at: string | null;
  scanner_name: string | null;
};

/** Minimal attendee row from desk search (no email/phone). */
export type DeskAttendee = {
  id: string;
  public_code: string;
  ticket_type_name: string;
  status: string;
  holder_name: string;
  checked_in_at: string | null;
};

export type ScannerSession = {
  id: string;
  event_id: string;
  user_id: string;
  status: string;
  device_label: string | null;
  started_at: string;
  ended_at: string | null;
  scanner_name: string | null;
};

export type CheckInLog = {
  id: string;
  event_id: string;
  ticket_id: string | null;
  ticket_public_code: string | null;
  outcome: string;
  method: string;
  detail: string | null;
  override_reason: string | null;
  holder_name: string | null;
  ticket_type_name: string | null;
  created_at: string;
  scanner_name: string | null;
};

export type CheckInStats = {
  event_id: string;
  total_tickets: number;
  checked_in: number;
  remaining: number;
  successful_scans: number;
  duplicate_scans: number;
  invalid_scans: number;
  override_scans: number;
};

export async function startScannerSession(input: {
  event_id: string;
  device_label?: string;
}): Promise<ScannerSession> {
  return apiRequest<ScannerSession>("/checkins/sessions", {
    method: "POST",
    body: input,
  });
}

export async function endScannerSession(sessionId: string): Promise<ScannerSession> {
  return apiRequest<ScannerSession>(`/checkins/sessions/${sessionId}/end`, {
    method: "POST",
  });
}

export async function validateQr(input: {
  event_id: string;
  qr_payload: string;
  session_id?: string;
}): Promise<ScanResult> {
  return apiRequest<ScanResult>("/checkins/validate", { method: "POST", body: input });
}

export async function scanTicket(input: {
  event_id: string;
  qr_payload?: string;
  public_code?: string;
  session_id?: string;
}): Promise<ScanResult> {
  return apiRequest<ScanResult>("/checkins/scan", { method: "POST", body: input });
}

export async function searchAttendees(
  eventId: string,
  q: string,
): Promise<DeskAttendee[]> {
  return apiRequest<DeskAttendee[]>(
    `/checkins/events/${eventId}/search?q=${encodeURIComponent(q)}`,
  );
}

export async function fetchCheckIns(eventId: string): Promise<CheckInLog[]> {
  return apiRequest<CheckInLog[]>(`/checkins/events/${eventId}`);
}

export async function fetchCheckInStats(eventId: string): Promise<CheckInStats> {
  return apiRequest<CheckInStats>(`/checkins/events/${eventId}/stats`);
}

export type StaffAssignment = {
  id: string;
  event_id: string;
  user_id: string;
  role_label: string;
  user_email?: string | null;
  user_name?: string | null;
  created_at: string;
};

export async function fetchEventStaff(
  eventId: string,
): Promise<StaffAssignment[]> {
  return apiRequest<StaffAssignment[]>(`/checkins/events/${eventId}/staff`);
}

export async function assignEventStaff(
  eventId: string,
  email: string,
): Promise<StaffAssignment> {
  return apiRequest<StaffAssignment>(`/checkins/events/${eventId}/staff`, {
    method: "POST",
    body: { email },
  });
}

export async function unassignEventStaff(
  eventId: string,
  assignmentId: string,
): Promise<void> {
  await apiRequest<{ message: string }>(
    `/checkins/events/${eventId}/staff/${assignmentId}`,
    { method: "DELETE" },
  );
}
