import { apiRequest, apiUpload } from "@/lib/api";
import type {
  AdminSupportTicketFilters,
  SupportCase,
  SupportMeta,
  SupportPublicCreate,
  SupportSettings,
  SupportTicketCreate,
} from "@/lib/types/support";

function buildQuery(params: Record<string, string | undefined>): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== "") qs.set(key, value);
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/** Ticket number shown in UI (prefers ticket_number alias). */
export function supportTicketNumber(ticket: SupportCase): string {
  return ticket.ticket_number || ticket.case_number;
}

// --- Meta / settings ---

export async function fetchSupportMeta(): Promise<SupportMeta> {
  return apiRequest<SupportMeta>("/support/meta", { auth: false });
}

export async function fetchAdminSupportSettings(): Promise<SupportSettings> {
  return apiRequest<SupportSettings>("/admin/support/settings");
}

export async function updateAdminSupportSettings(
  body: Partial<SupportSettings>,
): Promise<SupportSettings> {
  return apiRequest<SupportSettings>("/admin/support/settings", {
    method: "PATCH",
    body,
  });
}

// --- Authenticated user / host tickets ---

export async function createSupportTicket(
  body: SupportTicketCreate,
): Promise<SupportCase> {
  return apiRequest<SupportCase>("/support/tickets", { method: "POST", body });
}

/** @deprecated Prefer createSupportTicket */
export async function createSupportCase(body: {
  subject: string;
  category: string;
  body: string;
  priority?: string;
  related_order_id?: string | null;
  related_event_id?: string | null;
}): Promise<SupportCase> {
  return createSupportTicket(body);
}

export async function createPublicSupportTicket(
  body: SupportPublicCreate,
): Promise<SupportCase> {
  return apiRequest<SupportCase>("/support/tickets/public", {
    method: "POST",
    body: { ...body, website: body.website ?? "" },
    auth: false,
  });
}

export async function postSupportDeflectionEvent(body: {
  event_type: string;
  topic?: string | null;
  session_key?: string | null;
  article_id?: string | null;
  article_slug?: string | null;
  meta?: Record<string, string | number | boolean>;
}): Promise<{ ok: boolean; event_type: string }> {
  return apiRequest("/support/deflection-events", {
    method: "POST",
    body,
    auth: false,
  });
}

export async function fetchMySupportTickets(): Promise<SupportCase[]> {
  return apiRequest<SupportCase[]>("/support/tickets");
}

/** @deprecated Prefer fetchMySupportTickets */
export async function fetchMySupportCases(): Promise<SupportCase[]> {
  return fetchMySupportTickets();
}

export async function fetchSupportTicket(id: string): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/tickets/${id}`);
}

/** @deprecated Prefer fetchSupportTicket */
export async function fetchSupportCase(id: string): Promise<SupportCase> {
  return fetchSupportTicket(id);
}

export async function fetchSupportTicketByNumber(
  ticketNumber: string,
  opts?: { email?: string; token?: string },
): Promise<SupportCase> {
  const q = buildQuery({ email: opts?.email, token: opts?.token });
  return apiRequest<SupportCase>(
    `/support/tickets/by-number/${encodeURIComponent(ticketNumber)}${q}`,
    { auth: false },
  );
}

export async function replySupportTicket(
  id: string,
  body: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/tickets/${id}/reply`, {
    method: "POST",
    body: { body },
  });
}

/** Legacy staff path still used by case desk */
export async function replySupportCase(
  id: string,
  body: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/messages`, {
    method: "POST",
    body: { body },
  });
}

export async function uploadSupportAttachment(
  id: string,
  file: File,
  isInternal = false,
): Promise<SupportCase> {
  const form = new FormData();
  form.append("file", file);
  form.append("is_internal", String(isInternal));
  return apiUpload<SupportCase>(`/support/tickets/${id}/attachments`, form);
}

// --- Legacy staff case list (agent desk) ---

export async function fetchStaffSupportCases(
  status?: string,
  filters?: Omit<AdminSupportTicketFilters, "status">,
): Promise<SupportCase[]> {
  const q = buildQuery({
    status,
    priority: filters?.priority,
    category: filters?.category,
    q: filters?.q,
  });
  return apiRequest<SupportCase[]>(`/support/cases${q}`);
}

export async function addSupportNote(
  id: string,
  body: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/notes`, {
    method: "POST",
    body: { body },
  });
}

export async function assignSupportCase(
  id: string,
  assignee_user_id?: string | null,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/assign`, {
    method: "POST",
    body: { assignee_user_id: assignee_user_id ?? null },
  });
}

export async function escalateSupportCase(
  id: string,
  escalation_level: string,
  note?: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/escalate`, {
    method: "POST",
    body: { escalation_level, note },
  });
}

export async function resolveSupportCase(id: string): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/resolve`, {
    method: "POST",
  });
}

export async function closeSupportCase(id: string): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/close`, {
    method: "POST",
  });
}

export async function archiveSupportCase(id: string): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/archive`, {
    method: "POST",
  });
}

// --- Admin support queue ---

export async function fetchAdminSupportTickets(
  filters: AdminSupportTicketFilters = {},
): Promise<SupportCase[]> {
  const q = buildQuery({
    status: filters.status,
    priority: filters.priority,
    category: filters.category,
    requester_context: filters.requester_context,
    assigned_to: filters.assigned_to,
    q: filters.q,
  });
  return apiRequest<SupportCase[]>(`/admin/support/tickets${q}`);
}

export async function fetchAdminSupportTicket(
  id: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}`);
}

export async function adminReplySupportTicket(
  id: string,
  body: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/reply`, {
    method: "POST",
    body: { body },
  });
}

export async function adminAddInternalNote(
  id: string,
  body: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/internal-note`, {
    method: "POST",
    body: { body },
  });
}

export async function adminAssignSupportTicket(
  id: string,
  assignee_user_id?: string | null,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/assign`, {
    method: "PATCH",
    body: { assignee_user_id: assignee_user_id ?? null },
  });
}

export async function adminUpdateSupportPriority(
  id: string,
  priority: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/priority`, {
    method: "PATCH",
    body: { priority },
  });
}

export async function adminUpdateSupportCategory(
  id: string,
  category: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/category`, {
    method: "PATCH",
    body: { category },
  });
}

export async function updateSupportCasePriority(
  id: string,
  priority: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/priority`, {
    method: "PATCH",
    body: { priority },
  });
}

export async function updateSupportCaseCategory(
  id: string,
  category: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/support/cases/${id}/category`, {
    method: "PATCH",
    body: { category },
  });
}

export async function adminUpdateSupportStatus(
  id: string,
  status: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/status`, {
    method: "PATCH",
    body: { status },
  });
}

export async function adminResolveSupportTicket(
  id: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/resolve`, {
    method: "POST",
  });
}

export async function adminCloseSupportTicket(
  id: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/close`, {
    method: "POST",
  });
}

export async function adminReopenSupportTicket(
  id: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/reopen`, {
    method: "POST",
  });
}

export async function adminEscalateSupportTicket(
  id: string,
  escalation_level: string,
  note?: string,
): Promise<SupportCase> {
  return apiRequest<SupportCase>(`/admin/support/tickets/${id}/escalate`, {
    method: "POST",
    body: { escalation_level, note },
  });
}
