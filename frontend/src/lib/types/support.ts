export type SupportMessage = {
  id: string;
  case_id: string;
  author_user_id: string | null;
  author_name: string | null;
  body: string;
  is_internal: boolean;
  created_at: string;
};

export type SupportInternalNote = {
  id: string;
  case_id: string;
  author_user_id: string;
  author_name: string | null;
  body: string;
  created_at: string;
};

export type SupportAttachment = {
  id: string;
  case_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  is_internal: boolean;
  created_at: string;
};

export type SupportEvent = {
  id: string;
  case_id: string;
  event_type: string;
  summary: string;
  is_public: boolean;
  created_at: string;
  actor_user_id: string | null;
};

export type SupportCase = {
  id: string;
  case_number: string;
  ticket_number?: string | null;
  requester_user_id: string | null;
  requester_email?: string | null;
  requester_name?: string | null;
  requester_context?: string;
  assignee_user_id: string | null;
  subject: string;
  category: string;
  status: string;
  priority: string;
  related_order_id: string | null;
  related_event_id: string | null;
  related_host_id?: string | null;
  escalation_level: string | null;
  help_suggestions_shown?: boolean;
  deflection_meta?: {
    topic?: string | null;
    suggested_article_ids?: string[];
    suggested_article_slugs?: string[];
    articles_clicked?: string[];
    referrer?: string | null;
    session_key?: string | null;
  } | null;
  resolved_at: string | null;
  closed_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
  messages: SupportMessage[];
  internal_notes: SupportInternalNote[];
  attachments?: SupportAttachment[];
  events?: SupportEvent[];
  public_token?: string | null;
};

export type SupportCategoryOption = {
  value: string;
  label: string;
};

export type SupportMeta = {
  categories: SupportCategoryOption[];
  statuses: string[];
  priorities: string[];
};

export type SupportSettings = {
  auto_assign_enabled: boolean;
  notify_on_urgent: boolean;
  public_form_enabled: boolean;
  default_priority: string;
};

export type SupportDeflectionMeta = {
  topic?: string | null;
  suggested_article_ids?: string[];
  suggested_article_slugs?: string[];
  articles_clicked?: string[];
  referrer?: string | null;
  session_key?: string | null;
  help_suggestions_shown?: boolean;
};

export type SupportTicketCreate = {
  subject: string;
  category: string;
  body: string;
  priority?: string;
  related_order_id?: string | null;
  related_event_id?: string | null;
  related_host_id?: string | null;
  requester_context?: string | null;
  deflection?: SupportDeflectionMeta | null;
};

export type SupportPublicCreate = {
  subject: string;
  category: string;
  body: string;
  requester_email: string;
  requester_name: string;
  priority?: string;
  /** Honeypot — must stay empty */
  website?: string;
  deflection?: SupportDeflectionMeta | null;
};

export type AdminSupportTicketFilters = {
  status?: string;
  priority?: string;
  category?: string;
  requester_context?: string;
  assigned_to?: string;
  q?: string;
};
