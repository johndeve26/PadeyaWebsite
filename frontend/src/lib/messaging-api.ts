import { ApiError, apiRequest, apiUpload, refreshTokens } from "@/lib/api";
import { getApiBaseUrl, getApiPrefix, getApiWsBaseUrl } from "@/lib/api-base";
import { getAccessToken } from "@/lib/auth/storage";
import type {
  AdminMessageReport,
  AttachmentUpload,
  ConnectContext,
  MessageItem,
  MessageNotification,
  MessageSettings,
  StarredList,
  ThreadDetail,
  ThreadList,
} from "@/lib/types/messaging";

const API_URL = getApiBaseUrl();
const API_PREFIX = getApiPrefix();

function xhrUploadJson<T>(
  path: string,
  formData: FormData,
  onProgress?: (pct: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}${API_PREFIX}${path}`);
    const access = getAccessToken();
    if (access) {
      xhr.setRequestHeader("Authorization", `Bearer ${access}`);
    }
    xhr.upload.onprogress = (ev) => {
      if (!onProgress || !ev.lengthComputable || ev.total <= 0) return;
      onProgress(Math.min(100, Math.round((ev.loaded / ev.total) * 100)));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch {
          reject(new ApiError(xhr.status, "Upload failed."));
        }
        return;
      }
      let detail = xhr.statusText || "Upload failed.";
      try {
        const data = JSON.parse(xhr.responseText) as { detail?: string };
        if (typeof data.detail === "string") detail = data.detail;
      } catch {
        // ignore
      }
      reject(new ApiError(xhr.status, detail));
    };
    xhr.onerror = () => reject(new ApiError(0, "Upload failed."));
    xhr.onabort = () => reject(new ApiError(0, "Upload failed."));
    xhr.send(formData);
  });
}

export async function fetchUnreadCount(): Promise<number> {
  const res = await apiRequest<{ unread_count: number }>("/messages/unread-count");
  return res.unread_count;
}

export async function fetchMessageNotifications(): Promise<{
  items: MessageNotification[];
}> {
  return apiRequest("/messages/notifications");
}

export async function fetchFanThreads(params: {
  filter?: string;
  q?: string;
  page?: number;
} = {}): Promise<ThreadList> {
  const sp = new URLSearchParams();
  if (params.filter) sp.set("filter", params.filter);
  if (params.q) sp.set("q", params.q);
  if (params.page) sp.set("page", String(params.page));
  const qs = sp.toString();
  return apiRequest(`/messages${qs ? `?${qs}` : ""}`);
}

export async function fetchHostThreads(params: {
  filter?: string;
  q?: string;
  page?: number;
} = {}): Promise<ThreadList> {
  const sp = new URLSearchParams();
  if (params.filter) sp.set("filter", params.filter);
  if (params.q) sp.set("q", params.q);
  if (params.page) sp.set("page", String(params.page));
  const qs = sp.toString();
  return apiRequest(`/host/messages${qs ? `?${qs}` : ""}`);
}

export async function fetchFanThread(threadId: string): Promise<ThreadDetail> {
  return apiRequest(`/messages/${encodeURIComponent(threadId)}`);
}

export async function fetchHostThread(threadId: string): Promise<ThreadDetail> {
  return apiRequest(`/host/messages/${encodeURIComponent(threadId)}`);
}

export async function createFanThread(body: {
  host_id?: string;
  host_username?: string;
  related_event_id?: string;
  related_merch_order_item_id?: string;
  subject?: string;
  body: string;
}): Promise<ThreadDetail> {
  return apiRequest("/messages/threads", { method: "POST", body });
}

export async function createHostThread(body: {
  fan_user_id?: string;
  fan_username?: string;
  related_event_id?: string;
  related_merch_order_item_id?: string;
  subject?: string;
  body: string;
}): Promise<ThreadDetail> {
  return apiRequest("/host/messages/threads", { method: "POST", body });
}

export async function sendFanMessage(
  threadId: string,
  body: string,
  attachmentIds?: string[],
  replyToMessageId?: string | null,
): Promise<MessageItem> {
  return apiRequest(`/messages/${encodeURIComponent(threadId)}/send`, {
    method: "POST",
    body: {
      body,
      attachment_ids: attachmentIds || [],
      reply_to_message_id: replyToMessageId || undefined,
    },
  });
}

export async function sendHostMessage(
  threadId: string,
  body: string,
  attachmentIds?: string[],
  replyToMessageId?: string | null,
): Promise<MessageItem> {
  return apiRequest(`/host/messages/${encodeURIComponent(threadId)}/send`, {
    method: "POST",
    body: {
      body,
      attachment_ids: attachmentIds || [],
      reply_to_message_id: replyToMessageId || undefined,
    },
  });
}

export async function editMessage(
  _threadId: string,
  messageId: string,
  body: string,
  asHost?: boolean,
): Promise<MessageItem> {
  const base = asHost ? "/host/messages" : "/messages";
  return apiRequest(`${base}/${encodeURIComponent(messageId)}`, {
    method: "PATCH",
    body: { body },
  });
}

export type PinnedList = {
  items: MessageItem[];
  total: number;
};

export async function listThreadPins(
  threadId: string,
  asHost?: boolean,
): Promise<PinnedList> {
  const base = asHost ? "/host/messages" : "/messages";
  return apiRequest(
    `${base}/threads/${encodeURIComponent(threadId)}/pins`,
  );
}

export type ThreadSearchResult = {
  items: MessageItem[];
  total: number;
  q: string;
  filters: {
    starred: boolean;
    pinned: boolean;
    has_attachments: boolean;
  };
};

export async function searchThreadMessages(
  threadId: string,
  opts: {
    q?: string;
    starred?: boolean;
    pinned?: boolean;
    hasAttachments?: boolean;
    asHost?: boolean;
  } = {},
): Promise<ThreadSearchResult> {
  const base = opts.asHost ? "/host/messages" : "/messages";
  const params = new URLSearchParams();
  if (opts.q?.trim()) params.set("q", opts.q.trim());
  if (opts.starred) params.set("starred", "true");
  if (opts.pinned) params.set("pinned", "true");
  if (opts.hasAttachments) params.set("has_attachments", "true");
  const qs = params.toString();
  return apiRequest(
    `${base}/threads/${encodeURIComponent(threadId)}/search${qs ? `?${qs}` : ""}`,
  );
}

export async function pinMessage(
  _threadId: string,
  messageId: string,
  asHost?: boolean,
): Promise<PinnedList> {
  const base = asHost ? "/host/messages" : "/messages";
  return apiRequest(`${base}/${encodeURIComponent(messageId)}/pin`, {
    method: "POST",
  });
}

export async function unpinMessage(
  _threadId: string,
  messageId: string,
  asHost?: boolean,
): Promise<PinnedList> {
  const base = asHost ? "/host/messages" : "/messages";
  return apiRequest(`${base}/${encodeURIComponent(messageId)}/unpin`, {
    method: "POST",
  });
}

export async function deleteMessageForMe(
  messageId: string,
  asHost?: boolean,
): Promise<MessageItem> {
  const base = asHost ? "/host/messages" : "/messages";
  return apiRequest(`${base}/${encodeURIComponent(messageId)}/delete`, {
    method: "POST",
    body: { scope: "for_me" },
  });
}

export async function starMessage(
  _threadId: string,
  messageId: string,
  asHost?: boolean,
): Promise<MessageItem> {
  const base = asHost ? "/host/messages" : "/messages";
  return apiRequest(`${base}/${encodeURIComponent(messageId)}/star`, {
    method: "POST",
  });
}

export async function unstarMessage(
  _threadId: string,
  messageId: string,
  asHost?: boolean,
): Promise<MessageItem> {
  const base = asHost ? "/host/messages" : "/messages";
  return apiRequest(`${base}/${encodeURIComponent(messageId)}/unstar`, {
    method: "POST",
  });
}

export async function listStarredMessages(
  asHost?: boolean,
  page = 1,
): Promise<StarredList> {
  const path = asHost ? "/host/messages/starred" : "/messages/starred";
  return apiRequest(`${path}?page=${page}`);
}

export async function uploadMessageAttachment(
  file: File,
  opts: {
    threadId: string;
    asHost?: boolean;
    onProgress?: (pct: number) => void;
  },
): Promise<AttachmentUpload> {
  const fd = new FormData();
  fd.append("file", file);
  const tid = encodeURIComponent(opts.threadId);
  const path = opts.asHost
    ? `/host/messages/threads/${tid}/attachments`
    : `/messages/threads/${tid}/attachments`;

  if (!opts.onProgress) {
    return apiUpload(path, fd);
  }

  try {
    return await xhrUploadJson<AttachmentUpload>(path, fd, opts.onProgress);
  } catch (err) {
    if (err instanceof ApiError && err.status === 401 && getAccessToken()) {
      const refreshed = await refreshTokens();
      if (refreshed) {
        return xhrUploadJson<AttachmentUpload>(path, fd, opts.onProgress);
      }
    }
    throw err;
  }
}

/** Browser WebSocket URL for messaging push (JWT query token). */
export function messagingWebSocketUrl(): string | null {
  if (typeof window === "undefined") return null;
  const token = getAccessToken();
  if (!token) return null;
  const base = getApiWsBaseUrl();
  return `${base}${API_PREFIX}/messages/ws?token=${encodeURIComponent(token)}`;
}

export async function markFanRead(threadId: string): Promise<void> {
  await apiRequest(`/messages/${encodeURIComponent(threadId)}/read`, {
    method: "PATCH",
  });
}

export async function markHostRead(threadId: string): Promise<void> {
  await apiRequest(`/host/messages/${encodeURIComponent(threadId)}/read`, {
    method: "PATCH",
  });
}

export async function archiveFanThread(threadId: string): Promise<void> {
  await apiRequest(`/messages/${encodeURIComponent(threadId)}/archive`, {
    method: "PATCH",
  });
}

export async function archiveHostThread(threadId: string): Promise<void> {
  await apiRequest(`/host/messages/${encodeURIComponent(threadId)}/archive`, {
    method: "PATCH",
  });
}

export async function acceptFanRequest(threadId: string): Promise<ThreadDetail> {
  return apiRequest(`/messages/${encodeURIComponent(threadId)}/accept`, {
    method: "POST",
    body: { accept: true },
  });
}

export async function reportFanThread(
  threadId: string,
  reason: string,
  details?: string,
): Promise<void> {
  await apiRequest(`/messages/${encodeURIComponent(threadId)}/report`, {
    method: "POST",
    body: { reason, details },
  });
}

export async function reportHostThread(
  threadId: string,
  reason: string,
  details?: string,
): Promise<void> {
  await apiRequest(`/host/messages/${encodeURIComponent(threadId)}/report`, {
    method: "POST",
    body: { reason, details },
  });
}

export async function blockUser(
  blockedUserId: string,
  reason?: string,
  asHost = false,
): Promise<void> {
  await apiRequest(asHost ? "/host/messages/block" : "/messages/block", {
    method: "POST",
    body: { blocked_user_id: blockedUserId, reason },
  });
}

export async function fetchMessageSettings(): Promise<MessageSettings> {
  return apiRequest("/messages/settings");
}

export async function updateMessageSettings(
  body: Partial<Omit<MessageSettings, "blocked_users">>,
): Promise<MessageSettings> {
  return apiRequest("/messages/settings", { method: "PATCH", body });
}

export async function unblockMessagingUser(
  blockedUserId: string,
  asHost = false,
): Promise<void> {
  await apiRequest(
    asHost
      ? `/host/messages/block/${encodeURIComponent(blockedUserId)}`
      : `/messages/block/${encodeURIComponent(blockedUserId)}`,
    { method: "DELETE" },
  );
}

export async function hostCanMessageFan(fanUserId: string): Promise<boolean> {
  const res = await apiRequest<{ allowed: boolean }>(
    `/host/messages/can-message/${encodeURIComponent(fanUserId)}`,
  );
  return res.allowed;
}

export async function hostCanMessageFanUsername(
  username: string,
): Promise<boolean> {
  const res = await apiRequest<{ allowed: boolean }>(
    `/host/messages/can-message-by-username/${encodeURIComponent(username)}`,
  );
  return res.allowed;
}

export async function fetchAdminMessageReports(): Promise<{
  items: AdminMessageReport[];
  total: number;
}> {
  return apiRequest("/admin/message-reports");
}

export async function fetchAdminMessageReport(id: string): Promise<{
  id: string;
  thread_id: string;
  reason: string;
  details?: string | null;
  status: string;
  admin_notes?: string | null;
  reporter_display_name: string;
  reported_display_name: string;
  host_display_name?: string | null;
  thread_type?: string | null;
  connect_context?: ConnectContext | null;
  messages: MessageItem[];
  created_at: string;
}> {
  return apiRequest(`/admin/message-reports/${encodeURIComponent(id)}`);
}

export async function patchAdminMessageReport(
  id: string,
  body: { status?: string; admin_notes?: string },
): Promise<void> {
  await apiRequest(`/admin/message-reports/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body,
  });
}

export async function hideAdminMessage(messageId: string): Promise<void> {
  await apiRequest(`/admin/messages/${encodeURIComponent(messageId)}/hide`, {
    method: "PATCH",
  });
}

export async function restoreAdminMessage(messageId: string): Promise<void> {
  await apiRequest(`/admin/messages/${encodeURIComponent(messageId)}/restore`, {
    method: "PATCH",
  });
}

export async function hideAdminAttachment(
  attachmentId: string,
): Promise<AttachmentUpload> {
  return apiRequest(
    `/admin/messages/attachments/${encodeURIComponent(attachmentId)}/hide`,
    { method: "PATCH" },
  );
}

export async function restoreAdminAttachment(
  attachmentId: string,
): Promise<AttachmentUpload> {
  return apiRequest(
    `/admin/messages/attachments/${encodeURIComponent(attachmentId)}/restore`,
    { method: "PATCH" },
  );
}

export async function deleteAdminAttachment(
  attachmentId: string,
): Promise<AttachmentUpload> {
  return apiRequest(
    `/admin/messages/attachments/${encodeURIComponent(attachmentId)}/delete`,
    { method: "PATCH" },
  );
}

export async function reviewAdminAttachment(
  attachmentId: string,
): Promise<AttachmentUpload> {
  return apiRequest(
    `/admin/messages/attachments/${encodeURIComponent(attachmentId)}/review`,
    { method: "PATCH" },
  );
}
