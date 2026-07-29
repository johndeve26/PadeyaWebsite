export type MessageParticipant = {
  display_name: string;
  username?: string | null;
  role: string;
  legacy_path?: string | null;
  passport_path?: string | null;
  avatar_url?: string | null;
  gender?: string | null;
  gender_short?: string | null;
  gender_label?: string | null;
  gender_visible?: boolean;
};

export type RelatedEventChip = {
  id: string;
  title: string;
  slug: string;
  path: string;
  banner_url?: string | null;
};

export type ConnectContext = {
  badge: string;
  context_label: string;
  reasons?: { code: string; label: string }[];
};

export type ThreadListItem = {
  id: string;
  status: string;
  subject?: string | null;
  last_message_preview?: string | null;
  last_message_at?: string | null;
  unread: boolean;
  is_request: boolean;
  archived?: boolean;
  blocked?: boolean;
  related_event?: RelatedEventChip | null;
  counterpart: MessageParticipant;
  thread_type?: string;
  connect_context?: ConnectContext | null;
  created_at: string;
};

export type ThreadList = {
  items: ThreadListItem[];
  page: number;
  limit: number;
  total: number;
  unread_count: number;
};

export type MessageAttachment = {
  id: string;
  url: string;
  content_type: string;
  byte_size: number;
  original_filename?: string | null;
  width?: number | null;
  height?: number | null;
  status?: string;
  reviewed_at?: string | null;
};

export type MessageReplyTo = {
  reply_message_id: string;
  reply_author_display_name?: string;
  reply_body_preview?: string | null;
  reply_attachment_preview?: string | null;
  reply_created_at?: string | null;
  reply_is_unavailable?: boolean;
};

export type MessageItem = {
  id: string;
  thread_id: string;
  sender_role: string;
  sender_display_name: string;
  body: string;
  message_type: string;
  status: string;
  moderation_status: string;
  created_at: string;
  is_mine: boolean;
  attachments?: MessageAttachment[];
  edited_at?: string | null;
  reply_to?: MessageReplyTo | null;
  is_pinned?: boolean;
  is_starred?: boolean;
  /** Viewer soft-deleted this message for themselves only. */
  deleted_for_me?: boolean;
  /** Client-only: send failed before/without a server row. */
  client_failed?: boolean;
};

export type StarredMessageItem = {
  message: MessageItem;
  thread_id: string;
  thread_type?: string;
  counterpart: MessageParticipant;
  starred_at: string;
};

export type StarredList = {
  items: StarredMessageItem[];
  page: number;
  limit: number;
  total: number;
};

export type AttachmentUpload = {
  id: string;
  url: string;
  content_type: string;
  byte_size: number;
  original_filename?: string | null;
  width?: number | null;
  height?: number | null;
  status?: string;
};

export type ThreadDetail = {
  id: string;
  status: string;
  subject?: string | null;
  is_request: boolean;
  can_reply: boolean;
  /** Attachments only after request accepted / Fan Connect open; false when blocked. */
  can_attach?: boolean;
  blocked: boolean;
  archived?: boolean;
  counterpart_user_id?: string | null;
  related_event?: RelatedEventChip | null;
  counterpart: MessageParticipant;
  thread_type?: string;
  connect_context?: ConnectContext | null;
  messages: MessageItem[];
  pinned_messages?: MessageItem[];
  privacy_reminder: string;
  /** Counterpart's thread-level read cursor for Seen UI. */
  peer_read_at?: string | null;
  created_at: string;
};

export type BlockedUser = {
  user_id: string;
  display_name: string;
  username?: string | null;
  role: string;
  reason?: string | null;
  created_at: string;
};

export type MessageSettings = {
  allow_messages_from_hosts_i_follow: boolean;
  allow_messages_from_hosts_i_attended: boolean;
  allow_messages_from_public: boolean;
  message_requests_enabled: boolean;
  allow_messages_from_followers: boolean;
  allow_messages_from_ticket_buyers: boolean;
  allow_messages_from_public_host: boolean;
  allow_event_inquiries: boolean;
  auto_reply_enabled: boolean;
  auto_reply_message: string | null;
  blocked_users: BlockedUser[];
};

export type AdminMessageReport = {
  id: string;
  thread_id: string;
  reason: string;
  status: string;
  reporter_display_name: string;
  reported_display_name: string;
  host_display_name?: string | null;
  thread_type?: string | null;
  created_at: string;
  message_preview?: string | null;
};

export type MessageNotification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  link_path?: string | null;
  read_at?: string | null;
  created_at: string;
};
