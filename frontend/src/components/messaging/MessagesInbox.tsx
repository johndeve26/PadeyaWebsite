"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { DateSeparator } from "@/components/messaging/DateSeparator";
import { EmptyMessagesState } from "@/components/messaging/EmptyMessagesState";
import type { MessageAction } from "@/components/messaging/MessageActionMenu";
import { MessageBubble } from "@/components/messaging/MessageBubble";
import {
  MessageComposer,
  type ComposerEditTarget,
  type ComposerReplyTarget,
} from "@/components/messaging/MessageComposer";
import { MessagesMobileHomeLink } from "@/components/messaging/MessagesMobileHomeLink";
import { MessagingSocketStatus } from "@/components/messaging/MessagingSocketStatus";
import { ParticipantAvatar } from "@/components/messaging/ParticipantAvatar";
import { PinnedMessagesBar } from "@/components/messaging/PinnedMessagesBar";
import { RelatedEventMiniCard } from "@/components/messaging/RelatedEventMiniCard";
import { ReportMessageDialog } from "@/components/messaging/ReportMessageDialog";
import { StarredMessagesList } from "@/components/messaging/StarredMessagesList";
import { ThreadMobileHeaderBar } from "@/components/messaging/ThreadMobileHeaderBar";
import {
  ThreadSearch,
  type ThreadSearchFilter,
} from "@/components/messaging/ThreadSearch";
import { ThreadListItem } from "@/components/messaging/ThreadListItem";
import {
  Alert,
  Badge,
  Button,
  Input,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { useThreadRealtime } from "@/hooks/useThreadRealtime";
import { useTypingIndicator } from "@/hooks/useTypingIndicator";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { messageDayKey } from "@/lib/format-message-time";
import { formatTypingLabel } from "@/lib/messaging/typing-label";
import { USER_RESTRICTION_ACTION_MESSAGE } from "@/lib/user-restrictions";
import {
  acceptFanRequest,
  archiveFanThread,
  archiveHostThread,
  blockUser,
  deleteMessageForMe,
  editMessage,
  fetchFanThread,
  fetchFanThreads,
  fetchHostThread,
  fetchHostThreads,
  listStarredMessages,
  markFanRead,
  markHostRead,
  pinMessage,
  reportFanThread,
  reportHostThread,
  searchThreadMessages,
  sendFanMessage,
  sendHostMessage,
  starMessage,
  unpinMessage,
  unstarMessage,
  uploadMessageAttachment,
} from "@/lib/messaging-api";
import type {
  MessageItem,
  StarredMessageItem,
  ThreadDetail,
  ThreadListItem as Thread,
} from "@/lib/types/messaging";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "unread", label: "Unread" },
  { value: "requests", label: "Requests" },
  { value: "event", label: "Event inquiries" },
  { value: "starred", label: "Starred messages" },
  { value: "archived", label: "Archived" },
];

export function MessagesInbox({
  mode,
  basePath,
}: {
  mode: "fan" | "host";
  basePath: string;
}) {
  const params = useParams<{ threadId?: string }>();
  const threadId = params?.threadId;
  const searchParams = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { has } = useUserRestrictions();
  const cannotMessage = has("cannot_message");
  const filterParam = searchParams.get("filter") || "all";
  const filter = FILTERS.some((f) => f.value === filterParam)
    ? filterParam
    : "all";
  const focusMessageId = searchParams.get("m");
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Thread[]>([]);
  const [starredItems, setStarredItems] = useState<StarredMessageItem[]>([]);
  const [detail, setDetail] = useState<ThreadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(Boolean(threadId));
  const [error, setError] = useState<string | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [replyTo, setReplyTo] = useState<ComposerReplyTarget | null>(null);
  const [editTarget, setEditTarget] = useState<ComposerEditTarget | null>(null);
  const [highlightMessageId, setHighlightMessageId] = useState<string | null>(
    null,
  );
  const [threadSearchQ, setThreadSearchQ] = useState("");
  const [threadSearchFilter, setThreadSearchFilter] =
    useState<ThreadSearchFilter>("all");
  const [threadSearchResults, setThreadSearchResults] = useState<MessageItem[]>(
    [],
  );
  const [threadSearchLoading, setThreadSearchLoading] = useState(false);
  const [mobileThreadSearchOpen, setMobileThreadSearchOpen] = useState(false);
  const focusedFromStarredRef = useRef<string | null>(null);
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const asHost = mode === "host";
  const showingStarred = filter === "starred";

  const reloadThreads = useCallback(() => {
    void (
      mode === "host"
        ? fetchHostThreads({ filter, q: q.trim() || undefined })
        : fetchFanThreads({ filter, q: q.trim() || undefined })
    )
      .then((res) => setItems(res.items))
      .catch(() => undefined);
  }, [mode, filter, q]);

  const scrollMessagesToBottom = useCallback(
    (behavior: ScrollBehavior = "auto") => {
      const el = messagesScrollRef.current;
      if (!el) return;
      el.scrollTo({ top: el.scrollHeight, behavior });
    },
    [],
  );

  const handleMessagesScroll = useCallback(() => {
    const el = messagesScrollRef.current;
    if (!el) return;
    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distanceFromBottom < 96;
  }, []);

  useEffect(() => {
    stickToBottomRef.current = true;
  }, [threadId]);

  const { peerTyping, peerDisplayName, setTyping } =
    useTypingIndicator(threadId);
  const { status, isLive, peerReadAt, hydratePeerReadAt } = useThreadRealtime(
    threadId,
    {
      onMessageCreated: (eventThreadId, message) => {
        setDetail((prev) => {
          if (!prev || prev.id !== eventThreadId) return prev;
          if (prev.messages.some((m) => m.id === message.id)) return prev;
          const nextStatus =
            message.message_type === "system" ? prev.status : "active";
          return {
            ...prev,
            messages: [...prev.messages, message],
            is_request: false,
            status: nextStatus,
            can_reply: prev.can_reply,
            can_attach:
              nextStatus === "active" && prev.can_reply && !prev.blocked
                ? true
                : prev.can_attach,
          };
        });
        setItems((prev) => {
          const exists = prev.some((t) => t.id === eventThreadId);
          if (!exists) {
            reloadThreads();
            return prev;
          }
          return prev.map((t) =>
            t.id === eventThreadId
              ? {
                  ...t,
                  last_message_preview:
                    message.body ||
                    (message.attachments?.length
                      ? message.attachments.every((a) =>
                          (a.content_type || "").startsWith("image/"),
                        )
                        ? "Sent an image"
                        : "Sent a file"
                      : t.last_message_preview),
                  last_message_at: message.created_at,
                  unread:
                    threadId === eventThreadId
                      ? false
                      : message.is_mine
                        ? t.unread
                        : true,
                  is_request: false,
                }
              : t,
          );
        });
      },
      onThreadUpdated: (event) => {
        setItems((prev) =>
          prev.map((t) =>
            t.id === event.thread_id
              ? {
                  ...t,
                  status: event.status ?? t.status,
                  is_request:
                    event.is_request !== undefined
                      ? event.is_request
                      : t.is_request,
                  last_message_preview:
                    event.last_message_preview ?? t.last_message_preview,
                  last_message_at: event.last_message_at ?? t.last_message_at,
                  unread:
                    event.unread === undefined
                      ? threadId === event.thread_id
                        ? false
                        : t.unread
                      : event.unread,
                  blocked:
                    event.blocked !== undefined ? event.blocked : t.blocked,
                }
              : t,
          ),
        );
        setDetail((prev) => {
          if (!prev || prev.id !== event.thread_id) return prev;
          const nextStatus = event.status ?? prev.status;
          const nextBlocked =
            event.blocked !== undefined ? event.blocked : prev.blocked;
          const nextCanReply =
            event.can_reply !== undefined ? event.can_reply : prev.can_reply;
          const nextIsRequest =
            event.is_request !== undefined
              ? event.is_request
              : prev.is_request;
          return {
            ...prev,
            status: nextStatus,
            is_request: nextIsRequest,
            blocked: nextBlocked,
            can_reply: nextCanReply,
            can_attach:
              !nextBlocked &&
              !nextIsRequest &&
              nextStatus !== "request" &&
              nextStatus !== "blocked" &&
              nextStatus !== "closed" &&
              nextCanReply,
          };
        });
      },
      onThreadDisabled: (event) => {
        setItems((prev) =>
          prev.map((t) =>
            t.id === event.thread_id
              ? {
                  ...t,
                  status: event.status ?? t.status,
                  blocked: event.blocked ?? true,
                  is_request: false,
                }
              : t,
          ),
        );
        setDetail((prev) => {
          if (!prev || prev.id !== event.thread_id) return prev;
          return {
            ...prev,
            status: event.status ?? prev.status,
            blocked: event.blocked ?? true,
            can_reply: false,
            can_attach: false,
          };
        });
      },
      onConnectionAccepted: (event) => {
        reloadThreads();
        if (threadId === event.thread_id) {
          void (
            mode === "host"
              ? fetchHostThread(event.thread_id)
              : fetchFanThread(event.thread_id)
          )
            .then(setDetail)
            .catch(() => undefined);
        }
      },
      onConnectionRemoved: () => {
        reloadThreads();
      },
      onMessageUpdated: (event) => {
        // Delivery status + edits can arrive for the open thread; list preview
        // refresh comes from thread.updated when the latest message changes.
        if (event.thread_id !== threadId) return;
        setDetail((prev) => {
          if (!prev || prev.id !== event.thread_id) return prev;
          if (event.message) {
            const nextMessages = prev.messages.map((m) =>
              m.id === event.message!.id ? event.message! : m,
            );
            const nextPinned = (prev.pinned_messages || []).map((m) =>
              m.id === event.message!.id ? event.message! : m,
            );
            return {
              ...prev,
              messages: nextMessages,
              pinned_messages: nextPinned,
            };
          }
          if (event.message_id) {
            return {
              ...prev,
              messages: prev.messages.map((m) =>
                m.id === event.message_id
                  ? { ...m, status: event.status || m.status }
                  : m,
              ),
            };
          }
          return prev;
        });
      },
      onMessageDeleted: (event) => {
        if (event.thread_id !== threadId) return;
        setDetail((prev) => {
          if (!prev || prev.id !== event.thread_id) return prev;
          const redacted =
            event.message ||
            ({
              body: "[Message hidden by moderation]",
              attachments: [],
              status: "hidden",
              is_pinned: false,
            } as Partial<MessageItem>);
          return {
            ...prev,
            messages: prev.messages.map((m) =>
              m.id === event.message_id ? { ...m, ...redacted } : m,
            ),
            pinned_messages: (prev.pinned_messages || []).filter(
              (m) => m.id !== event.message_id,
            ),
          };
        });
      },
      onMessagePinned: (event) => {
        if (event.thread_id !== threadId) return;
        const pinnedIds = new Set(
          (event.pinned_messages || []).map((m) => m.id),
        );
        setDetail((prev) => {
          if (!prev || prev.id !== event.thread_id) return prev;
          return {
            ...prev,
            pinned_messages: event.pinned_messages || [],
            messages: prev.messages.map((m) => ({
              ...m,
              is_pinned: pinnedIds.has(m.id),
            })),
          };
        });
      },
    },
  );

  const scrollToMessage = useCallback(
    (messageId: string, unavailable?: boolean) => {
      stickToBottomRef.current = false;
      if (unavailable) {
        toast.push({
          tone: "info",
          title: "Original message unavailable",
        });
        return;
      }
      const loaded = detail?.messages.some((m) => m.id === messageId);
      const el = document.getElementById(`msg-${messageId}`);
      if (el && loaded) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        setHighlightMessageId(messageId);
        window.setTimeout(() => {
          setHighlightMessageId((cur) => (cur === messageId ? null : cur));
        }, 1600);
        return;
      }
      // Original not in the loaded thread window — refresh once, then give up safely.
      if (!threadId) {
        toast.push({ tone: "info", title: "Original message unavailable" });
        return;
      }
      void (
        mode === "host" ? fetchHostThread(threadId) : fetchFanThread(threadId)
      )
        .then((data) => {
          setDetail(data);
          queueMicrotask(() => {
            const target = document.getElementById(`msg-${messageId}`);
            if (!target) {
              toast.push({
                tone: "info",
                title: "Original message unavailable",
              });
              return;
            }
            target.scrollIntoView({ behavior: "smooth", block: "center" });
            setHighlightMessageId(messageId);
            window.setTimeout(() => {
              setHighlightMessageId((cur) => (cur === messageId ? null : cur));
            }, 1600);
          });
        })
        .catch(() => {
          toast.push({ tone: "info", title: "Original message unavailable" });
        });
    },
    [detail?.messages, mode, threadId, toast],
  );

  useEffect(() => {
    if (!threadId || detailLoading || !detail || detail.id !== threadId) return;
    if (focusMessageId) return;
    if (!stickToBottomRef.current) return;

    const run = () => scrollMessagesToBottom("auto");
    run();
    const raf = requestAnimationFrame(run);
    const t = window.setTimeout(run, 0);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(t);
    };
  }, [
    threadId,
    detailLoading,
    detail,
    focusMessageId,
    detail?.messages.length,
    peerTyping,
    scrollMessagesToBottom,
  ]);

  useEffect(() => {
    const el = messagesScrollRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (stickToBottomRef.current) scrollMessagesToBottom("auto");
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [threadId, scrollMessagesToBottom]);

  // From Starred messages list: open thread and scroll to the saved message.
  useEffect(() => {
    if (!focusMessageId) {
      focusedFromStarredRef.current = null;
      return;
    }
    if (!threadId || detailLoading || !detail) return;
    if (detail.id !== threadId) return;
    if (focusedFromStarredRef.current === focusMessageId) return;
    focusedFromStarredRef.current = focusMessageId;
    scrollToMessage(focusMessageId);
    const params = new URLSearchParams(searchParams.toString());
    if (!params.has("m")) return;
    params.delete("m");
    const qs = params.toString();
    router.replace(
      qs ? `${basePath}/${threadId}?${qs}` : `${basePath}/${threadId}`,
      { scroll: false },
    );
  }, [
    focusMessageId,
    threadId,
    detailLoading,
    detail,
    searchParams,
    router,
    basePath,
    scrollToMessage,
  ]);

  async function handleMessageAction(
    action: MessageAction,
    message: MessageItem,
  ) {
    if (!detail || !threadId) return;
    const tid = threadId;
    try {
      if (action === "reply") {
        setEditTarget(null);
        const attLabel =
          message.attachments?.length === 1
            ? message.attachments[0].original_filename || "Attachment"
            : message.attachments?.length
              ? "Attachment"
              : null;
        setReplyTo({
          id: message.id,
          preview: message.body?.trim() || attLabel || "Message",
          senderName: message.is_mine
            ? "You"
            : message.sender_display_name,
        });
        return;
      }
      if (action === "edit") {
        setReplyTo(null);
        setEditTarget({ id: message.id, body: message.body || "" });
        return;
      }
      if (action === "copy") {
        await navigator.clipboard.writeText(message.body || "");
        toast.push({ tone: "success", title: "Copied" });
        return;
      }
      if (action === "pin") {
        const pins = await pinMessage(tid, message.id, asHost);
        const pinnedIds = new Set(pins.items.map((m) => m.id));
        setDetail((prev) =>
          prev
            ? {
                ...prev,
                pinned_messages: pins.items,
                messages: prev.messages.map((m) => ({
                  ...m,
                  is_pinned: pinnedIds.has(m.id),
                })),
              }
            : prev,
        );
        return;
      }
      if (action === "unpin") {
        const pins = await unpinMessage(tid, message.id, asHost);
        const pinnedIds = new Set(pins.items.map((m) => m.id));
        setDetail((prev) =>
          prev
            ? {
                ...prev,
                pinned_messages: pins.items,
                messages: prev.messages.map((m) => ({
                  ...m,
                  is_pinned: pinnedIds.has(m.id),
                })),
              }
            : prev,
        );
        return;
      }
      if (action === "star") {
        const msg = await starMessage(tid, message.id, asHost);
        setDetail((prev) =>
          prev
            ? {
                ...prev,
                messages: prev.messages.map((m) =>
                  m.id === msg.id ? msg : m,
                ),
              }
            : prev,
        );
        if (showingStarred) {
          void listStarredMessages(asHost).then((res) =>
            setStarredItems(res.items),
          );
        }
        return;
      }
      if (action === "unstar") {
        const msg = await unstarMessage(tid, message.id, asHost);
        setDetail((prev) =>
          prev
            ? {
                ...prev,
                messages: prev.messages.map((m) =>
                  m.id === msg.id ? msg : m,
                ),
              }
            : prev,
        );
        setStarredItems((prev) =>
          prev.filter((row) => row.message.id !== msg.id),
        );
        return;
      }
      if (action === "delete_for_me") {
        if (
          !window.confirm(
            "Delete this message for you? The other person will still see it.",
          )
        ) {
          return;
        }
        const msg = await deleteMessageForMe(message.id, asHost);
        setDetail((prev) =>
          prev
            ? {
                ...prev,
                messages: prev.messages.map((m) =>
                  m.id === msg.id ? msg : m,
                ),
                pinned_messages: (prev.pinned_messages || []).filter(
                  (m) => m.id !== msg.id,
                ),
              }
            : prev,
        );
        setStarredItems((prev) =>
          prev.filter((row) => row.message.id !== msg.id),
        );
        setItems((prev) =>
          prev.map((t) =>
            t.id === tid &&
            (t.last_message_preview === message.body ||
              detail.messages[detail.messages.length - 1]?.id === message.id)
              ? { ...t, last_message_preview: "Message deleted" }
              : t,
          ),
        );
        return;
      }
      if (action === "report") {
        setReportOpen(true);
        return;
      }
      if (action === "block") {
        const peerId = detail.counterpart_user_id;
        if (!peerId || detail.blocked) return;
        if (
          !window.confirm(
            `Block ${detail.counterpart.display_name}? They won’t be able to message you.`,
          )
        ) {
          return;
        }
        await blockUser(peerId, undefined, mode === "host");
        setDetail({ ...detail, blocked: true, can_reply: false });
        toast.push({ tone: "success", title: "User blocked" });
      }
    } catch (err) {
      toast.push({
        tone: "danger",
        title: err instanceof ApiError ? err.detail : "Action failed",
      });
    }
  }

  function setFilter(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "all") params.delete("filter");
    else params.set("filter", next);
    const qs = params.toString();
    const path = threadId ? `${basePath}/${threadId}` : basePath;
    router.replace(qs ? `${path}?${qs}` : path, { scroll: false });
  }

  useEffect(() => {
    let active = true;
    const t = window.setTimeout(() => {
      void (async () => {
        try {
          if (filter === "starred") {
            const res = await listStarredMessages(mode === "host");
            if (!active) return;
            setStarredItems(res.items);
            setItems([]);
            setError(null);
          } else {
            const res =
              mode === "host"
                ? await fetchHostThreads({ filter, q: q.trim() || undefined })
                : await fetchFanThreads({ filter, q: q.trim() || undefined });
            if (!active) return;
            setItems(res.items);
            setStarredItems([]);
            setError(null);
          }
        } catch (err) {
          if (!active) return;
          setError(err instanceof ApiError ? err.detail : "Failed to load messages");
        } finally {
          if (active) setLoading(false);
        }
      })();
    }, 150);
    return () => {
      active = false;
      window.clearTimeout(t);
    };
  }, [mode, filter, q]);

  useEffect(() => {
    queueMicrotask(() => {
      setReplyTo(null);
      setEditTarget(null);
      setThreadSearchQ("");
      setThreadSearchFilter("all");
      setThreadSearchResults([]);
      setMobileThreadSearchOpen(false);
    });
  }, [threadId]);

  const threadSearchActive =
    Boolean(threadSearchQ.trim()) || threadSearchFilter !== "all";

  useEffect(() => {
    if (!threadId || !threadSearchActive) return;
    let cancelled = false;
    const t = window.setTimeout(() => {
      if (!cancelled) setThreadSearchLoading(true);
      void searchThreadMessages(threadId, {
        q: threadSearchQ,
        starred: threadSearchFilter === "starred",
        pinned: threadSearchFilter === "pinned",
        hasAttachments: threadSearchFilter === "attachments",
        asHost,
      })
        .then((res) => {
          if (!cancelled) setThreadSearchResults(res.items);
        })
        .catch(() => {
          if (!cancelled) setThreadSearchResults([]);
        })
        .finally(() => {
          if (!cancelled) setThreadSearchLoading(false);
        });
    }, 220);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [
    threadId,
    threadSearchQ,
    threadSearchFilter,
    threadSearchActive,
    asHost,
  ]);

  useEffect(() => {
    if (!threadId) return;
    let active = true;
    void (async () => {
      try {
        const data =
          mode === "host"
            ? await fetchHostThread(threadId)
            : await fetchFanThread(threadId);
        if (!active) return;
        setDetail(data);
        setDetailLoading(false);
        hydratePeerReadAt(data.peer_read_at);
        // Clear unread in the list immediately; REST + WS keep peers/badges in sync.
        setItems((prev) =>
          prev.map((t) =>
            t.id === threadId ? { ...t, unread: false } : t,
          ),
        );
        // REST mark-read publishes WS receipts + unread_count to participants.
        if (mode === "host") await markHostRead(threadId);
        else await markFanRead(threadId);
      } catch (err) {
        if (!active) return;
        setDetail(null);
        setDetailLoading(false);
        setError(err instanceof ApiError ? err.detail : "Thread not found");
      }
    })();
    return () => {
      active = false;
    };
  }, [threadId, mode, hydratePeerReadAt]);

  // HTTP polling fallback when WebSocket is unavailable.
  useEffect(() => {
    if (isLive) return;
    const tick = () => {
      reloadThreads();
      if (!threadId) return;
      void (
        mode === "host" ? fetchHostThread(threadId) : fetchFanThread(threadId)
      )
        .then((data) => {
          setDetail((prev) => {
            if (!prev || prev.id !== data.id) return data;
            const known = new Set(prev.messages.map((m) => m.id));
            const merged = [
              ...prev.messages,
              ...data.messages.filter((m) => !known.has(m.id)),
            ];
            return { ...data, messages: merged };
          });
        })
        .catch(() => undefined);
    };
    const t = window.setInterval(tick, 20_000);
    return () => window.clearInterval(t);
  }, [isLive, reloadThreads, threadId, mode]);

  const activeDetail = threadId ? detail : null;

  const mobileListHidden = Boolean(threadId);

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card dark:bg-surface lg:flex-row">
      <aside
        className={`flex min-h-0 w-full shrink-0 flex-col border-b border-border lg:w-80 lg:border-b-0 lg:border-r ${
          mobileListHidden ? "hidden lg:flex" : "flex"
        }`}
      >
        <div className="space-y-2 border-b border-border p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <MessagesMobileHomeLink mode={mode} />
              <p className="text-sm font-extrabold text-foreground">Inbox</p>
              <MessagingSocketStatus status={status} />
            </div>
            <div className="flex items-center gap-3">
              <Link
                href={`${basePath}/notifications`}
                className="text-xs font-bold text-foreground underline-offset-2 hover:underline"
              >
                Alerts
              </Link>
              <Link
                href={`${basePath}/settings`}
                className="text-xs font-bold text-foreground underline-offset-2 hover:underline"
              >
                Settings
              </Link>
            </div>
          </div>
          <Input
            label="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Name or event"
          />
          <Select
            label="Filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            {FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto p-2">
          {loading ? <SkeletonLoader lines={5} /> : null}
          {!loading &&
          (showingStarred ? starredItems.length === 0 : items.length === 0) ? (
            <EmptyMessagesState
              title={
                showingStarred
                  ? "No starred messages"
                  : filter === "all" && !q.trim()
                    ? "No messages yet"
                    : "No conversations match"
              }
              description={
                showingStarred
                  ? "Star messages in a conversation to find them here."
                  : filter === "all" && !q.trim()
                    ? mode === "host"
                      ? "Message fans you have a real relationship with — conversations stay on Pàdéyá."
                      : "Message hosts from events, or connect with fans via Fan Connect — conversations stay on Pàdéyá."
                    : "Try another filter or clear search. Demo accounts with seeded chats use All."
              }
              ctaHref={
                showingStarred
                  ? basePath
                  : mode === "host"
                    ? "/host/audience"
                    : "/connect"
              }
              ctaLabel={
                showingStarred
                  ? "Inbox"
                  : mode === "host"
                    ? "Audience"
                    : "Fan Connect"
              }
            />
          ) : null}
          {showingStarred
            ? (
                <StarredMessagesList
                  items={starredItems}
                  basePath={basePath}
                />
              )
            : items.map((t) => (
                <ThreadListItem
                  key={t.id}
                  thread={t}
                  href={`${basePath}/${t.id}`}
                  active={t.id === threadId}
                />
              ))}
        </div>
      </aside>

      <section
        className={`flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden ${
          !threadId ? "hidden lg:flex" : "flex"
        }`}
      >
        {!threadId ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-muted-foreground">
              Select a conversation to read and reply.
            </p>
          </div>
        ) : detailLoading && !activeDetail ? (
          <div className="p-6">
            <SkeletonLoader lines={6} />
          </div>
        ) : activeDetail ? (
          <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden">
            <div className="min-h-0 shrink-0 overflow-hidden">
            <ThreadMobileHeaderBar
              detail={activeDetail}
              mode={mode}
              basePath={basePath}
              searchOpen={mobileThreadSearchOpen}
              onToggleSearch={() => setMobileThreadSearchOpen((v) => !v)}
              onAcceptRequest={() =>
                void acceptFanRequest(activeDetail.id).then((d) => setDetail(d))
              }
              onArchive={() =>
                void (mode === "host"
                  ? archiveHostThread(activeDetail.id)
                  : archiveFanThread(activeDetail.id)
                ).then(() => {
                  toast.push({ tone: "success", title: "Archived" });
                  router.push(basePath);
                })
              }
              onBlock={() => {
                if (
                  !activeDetail.counterpart_user_id ||
                  activeDetail.blocked ||
                  !window.confirm(
                    `Block ${activeDetail.counterpart.display_name}? They won’t be able to message you.`,
                  )
                ) {
                  return;
                }
                void blockUser(
                  activeDetail.counterpart_user_id,
                  undefined,
                  mode === "host",
                )
                  .then(() => {
                    setDetail({ ...activeDetail, blocked: true, can_reply: false });
                    toast.push({ tone: "success", title: "User blocked" });
                  })
                  .catch((err) =>
                    toast.push({
                      tone: "danger",
                      title:
                        err instanceof ApiError ? err.detail : "Could not block",
                    }),
                  );
              }}
              onReport={() => setReportOpen(true)}
            />
            <header className="hidden shrink-0 flex-wrap items-start justify-between gap-3 border-b border-border p-4 md:flex">
              <div className="flex min-w-0 items-start gap-3">
                <ParticipantAvatar
                  name={activeDetail.counterpart.display_name}
                  avatarUrl={activeDetail.counterpart.avatar_url}
                  size="lg"
                />
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      href={basePath}
                      className="text-sm font-semibold text-muted-foreground lg:hidden"
                    >
                      ← Inbox
                    </Link>
                    <h2 className="text-lg font-extrabold text-heading">
                      {activeDetail.counterpart.display_name}
                    </h2>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {activeDetail.thread_type === "fan_fan" ||
                    activeDetail.connect_context ? (
                      <Badge tone="accent" size="sm">
                        {activeDetail.connect_context?.badge || "Fan Connect"}
                      </Badge>
                    ) : activeDetail.counterpart.role ? (
                      <Badge tone="outline" size="sm">
                        {activeDetail.counterpart.role}
                      </Badge>
                    ) : null}
                    {activeDetail.is_request ? (
                      <Badge tone="warning" size="sm">
                        Request
                      </Badge>
                    ) : null}
                    {activeDetail.archived ? (
                      <Badge tone="neutral" size="sm">
                        Archived
                      </Badge>
                    ) : null}
                    {activeDetail.status === "reported" ? (
                      <Badge tone="danger" size="sm">
                        Reported
                      </Badge>
                    ) : null}
                    {activeDetail.blocked ? (
                      <Badge tone="danger" size="sm">
                        Blocked
                      </Badge>
                    ) : null}
                  </div>
                  {activeDetail.connect_context?.context_label ? (
                    <p className="text-xs font-medium text-primary/90">
                      {activeDetail.connect_context.context_label}
                    </p>
                  ) : null}
                  {activeDetail.counterpart.username ? (
                    <p className="text-xs text-muted-foreground">
                      @{activeDetail.counterpart.username}
                    </p>
                  ) : null}
                  {activeDetail.counterpart.legacy_path ||
                  activeDetail.counterpart.passport_path ? (
                    <Link
                      href={
                        activeDetail.counterpart.legacy_path ||
                        activeDetail.counterpart.passport_path ||
                        "#"
                      }
                      className="text-sm font-semibold text-foreground underline-offset-2 hover:underline"
                    >
                      View profile
                    </Link>
                  ) : null}
                  <p className="text-[11px] text-muted-foreground">
                    Started {formatDateTime(activeDetail.created_at)}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {activeDetail.is_request && mode === "host" ? (
                  <Button
                    size="sm"
                    onClick={() =>
                      void acceptFanRequest(activeDetail.id).then((d) =>
                        setDetail(d),
                      )
                    }
                  >
                    Accept request
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    void (mode === "host"
                      ? archiveHostThread(activeDetail.id)
                      : archiveFanThread(activeDetail.id)
                    ).then(() => {
                      toast.push({ tone: "success", title: "Archived" });
                      router.push(basePath);
                    })
                  }
                >
                  Archive
                </Button>
                {activeDetail.counterpart_user_id && !activeDetail.blocked ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      if (
                        !window.confirm(
                          `Block ${activeDetail.counterpart.display_name}? They won’t be able to message you.`,
                        )
                      ) {
                        return;
                      }
                      void blockUser(
                        activeDetail.counterpart_user_id!,
                        undefined,
                        mode === "host",
                      )
                        .then(() => {
                          setDetail({ ...activeDetail, blocked: true, can_reply: false });
                          toast.push({ tone: "success", title: "User blocked" });
                        })
                        .catch((err) =>
                          toast.push({
                            tone: "danger",
                            title:
                              err instanceof ApiError
                                ? err.detail
                                : "Could not block",
                          }),
                        );
                    }}
                  >
                    Block
                  </Button>
                ) : null}
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => setReportOpen(true)}
                >
                  Report
                </Button>
              </div>
            </header>

            <ThreadSearch
              className={cn(
                !mobileThreadSearchOpen &&
                  !threadSearchActive &&
                  "max-md:hidden",
              )}
              query={threadSearchQ}
              filter={threadSearchFilter}
              results={threadSearchActive ? threadSearchResults : []}
              loading={threadSearchActive && threadSearchLoading}
              onQueryChange={setThreadSearchQ}
              onFilterChange={setThreadSearchFilter}
              onSelect={(id) => scrollToMessage(id)}
              onClear={() => {
                setThreadSearchQ("");
                setThreadSearchFilter("all");
                setThreadSearchResults([]);
              }}
            />

            {activeDetail.related_event ? (
              <div className="hidden md:block">
                <RelatedEventMiniCard event={activeDetail.related_event} />
              </div>
            ) : null}

            {activeDetail.is_request ? (
              <Alert tone="info" title="Message request" className="m-3 hidden md:block">
                {mode === "host"
                  ? "This conversation started without a strong relationship. Accept by replying, or report / archive if unwanted."
                  : "Your message is pending. The host hasn’t accepted this request yet — you’ll be able to keep chatting once they reply."}
              </Alert>
            ) : null}

            {activeDetail.blocked ? (
              <Alert tone="warning" title="Messaging blocked" className="m-3 hidden md:block">
                This conversation is blocked. You can’t send new messages here.
              </Alert>
            ) : null}

            <div className="max-md:hidden">
            <PinnedMessagesBar
              pinned={activeDetail.pinned_messages || []}
              onSelect={(id) => scrollToMessage(id)}
            />
            </div>
            </div>

            <div
              ref={messagesScrollRef}
              onScroll={handleMessagesScroll}
              className="min-h-0 space-y-2 overflow-y-auto overscroll-contain p-3 md:p-4"
            >
              {activeDetail.is_request ? (
                <Alert tone="info" title="Message request" className="md:hidden">
                  {mode === "host"
                    ? "Accept by replying, or use More for archive / report."
                    : "Pending until they reply — you can keep waiting here."}
                </Alert>
              ) : null}
              {activeDetail.blocked ? (
                <Alert tone="warning" title="Messaging blocked" className="md:hidden">
                  You can’t send new messages in this thread.
                </Alert>
              ) : null}
              {activeDetail.messages.map((m, idx, arr) => {
                const dayKey = messageDayKey(m.created_at);
                const prevKey =
                  idx > 0 ? messageDayKey(arr[idx - 1].created_at) : null;
                const showDay = Boolean(dayKey && dayKey !== prevKey);
                return (
                  <div key={m.id} className="space-y-2">
                    {showDay ? (
                      <DateSeparator createdAt={m.created_at} />
                    ) : null}
                    <MessageBubble
                      message={m}
                      peerReadAt={peerReadAt}
                      canReply={activeDetail.can_reply && !activeDetail.blocked}
                      canPin={
                        Boolean(activeDetail.can_reply) &&
                        !activeDetail.blocked &&
                        activeDetail.status !== "closed"
                      }
                      canStar
                      canReport={
                        m.message_type !== "system" &&
                        m.sender_role !== "system"
                      }
                      canBlock={
                        Boolean(activeDetail.counterpart_user_id) &&
                        !activeDetail.blocked &&
                        !m.is_mine &&
                        m.message_type !== "system" &&
                        m.sender_role !== "system"
                      }
                      highlighted={highlightMessageId === m.id}
                      onAction={handleMessageAction}
                      onReplyTap={scrollToMessage}
                    />
                  </div>
                );
              })}
              {peerTyping ? (
                <p
                  className="px-1 text-xs font-semibold text-muted-foreground"
                  aria-live="polite"
                >
                  {formatTypingLabel(
                    // fan_fan: display name only (never username / contact).
                    peerDisplayName ||
                      activeDetail.counterpart.display_name,
                  )}
                </p>
              ) : null}
            </div>

            <MessageComposer
              disabled={
                cannotMessage ||
                !activeDetail.can_reply ||
                activeDetail.blocked
              }
              disabledReason={
                cannotMessage
                  ? USER_RESTRICTION_ACTION_MESSAGE
                  : activeDetail.blocked
                    ? "Messaging is blocked."
                    : !activeDetail.can_reply
                      ? "You cannot reply in this thread."
                      : undefined
              }
              privacyReminder={activeDetail.privacy_reminder}
              onTyping={setTyping}
              replyTo={replyTo}
              onCancelReply={() => setReplyTo(null)}
              editTarget={editTarget}
              onCancelEdit={() => setEditTarget(null)}
              onSaveEdit={async (body) => {
                if (!editTarget) return;
                const msg = await editMessage(
                  activeDetail.id,
                  editTarget.id,
                  body,
                  asHost,
                );
                setDetail((prev) =>
                  prev
                    ? {
                        ...prev,
                        messages: prev.messages.map((m) =>
                          m.id === msg.id ? msg : m,
                        ),
                        pinned_messages: (prev.pinned_messages || []).map(
                          (m) => (m.id === msg.id ? msg : m),
                        ),
                      }
                    : prev,
                );
                // Product updates inbox preview to the new body (not a generic “edited” stub).
                setItems((prev) =>
                  prev.map((t) => {
                    if (t.id !== activeDetail.id) return t;
                    const lastId =
                      activeDetail.messages[activeDetail.messages.length - 1]
                        ?.id;
                    if (lastId !== msg.id) return t;
                    return {
                      ...t,
                      last_message_preview:
                        msg.body?.trim() || t.last_message_preview,
                      last_message_at:
                        msg.edited_at || msg.created_at || t.last_message_at,
                    };
                  }),
                );
                setEditTarget(null);
              }}
              onUpload={
                (
                  activeDetail.can_attach ??
                  (!activeDetail.is_request &&
                    !activeDetail.blocked &&
                    activeDetail.can_reply &&
                    activeDetail.status !== "request")
                )
                  ? async (file, onProgress) =>
                      uploadMessageAttachment(file, {
                        asHost: mode === "host",
                        threadId: activeDetail.id,
                        onProgress,
                      })
                  : undefined
              }
              onSend={async (body, attachmentIds) => {
                const replyId = replyTo?.id;
                try {
                  const msg =
                    mode === "host"
                      ? await sendHostMessage(
                          activeDetail.id,
                          body,
                          attachmentIds,
                          replyId,
                        )
                      : await sendFanMessage(
                          activeDetail.id,
                          body,
                          attachmentIds,
                          replyId,
                        );
                  setReplyTo(null);
                  setDetail((prev) => {
                    if (!prev || prev.id !== activeDetail.id) return prev;
                    if (prev.messages.some((m) => m.id === msg.id)) return prev;
                    return {
                      ...prev,
                      messages: [...prev.messages, msg],
                      is_request: false,
                      status: "active",
                    };
                  });
                  setItems((prev) =>
                    prev.map((t) =>
                      t.id === activeDetail.id
                        ? {
                            ...t,
                            last_message_preview:
                              msg.body?.trim() ||
                              (msg.attachments?.length
                                ? "Sent a file"
                                : t.last_message_preview),
                            last_message_at:
                              msg.created_at || t.last_message_at,
                            unread: false,
                            is_request: false,
                          }
                        : t,
                    ),
                  );
                } catch (err) {
                  const failed: MessageItem = {
                    id: `local-failed-${Date.now()}`,
                    thread_id: activeDetail.id,
                    sender_role: mode === "host" ? "host" : "fan",
                    sender_display_name: "You",
                    body,
                    message_type: "text",
                    status: "failed",
                    moderation_status: "clean",
                    created_at: new Date().toISOString(),
                    is_mine: true,
                    client_failed: true,
                    attachments: [],
                  };
                  setDetail((prev) =>
                    prev && prev.id === activeDetail.id
                      ? { ...prev, messages: [...prev.messages, failed] }
                      : prev,
                  );
                  throw err;
                }
              }}
            />
          </div>
        ) : (
          <div className="p-6">
            <Alert tone="danger" title="Unavailable">
              {error || "Conversation not found."}
            </Alert>
          </div>
        )}
      </section>

      <ReportMessageDialog
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        onSubmit={async (reason, details) => {
          if (!activeDetail) return;
          if (mode === "host")
            await reportHostThread(activeDetail.id, reason, details);
          else await reportFanThread(activeDetail.id, reason, details);
          toast.push({ tone: "success", title: "Report submitted" });
        }}
      />

    </div>
  );
}
