/**
 * Messaging + attachments frontend smoke checks.
 * Static contract tests (no browser / React runner).
 * Run: npm run test:messaging
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

function assertThemeSafeTokens(rel, source) {
  assert.match(
    source,
    /text-foreground|text-heading|text-muted-foreground|bg-card|border-border|bg-surface/,
    `${rel} should use semantic theme tokens for light/dark`,
  );
  const withoutInkHero = source.replace(
    /className="[^"]*\bbg-ink\b[\s\S]*?<\/section>/g,
    "",
  );
  assert.doesNotMatch(
    withoutInkHero,
    /\btext-ink\b/,
    `${rel} must not use text-ink on themed surfaces`,
  );
}

// --- Core files exist ---
const required = [
  "src/components/messaging/MessageComposer.tsx",
  "src/components/messaging/MessageAttachmentBlock.tsx",
  "src/components/messaging/MessageBubble.tsx",
  "src/components/messaging/MessagesInbox.tsx",
  "src/components/messaging/MessagingSocketStatus.tsx",
  "src/components/messaging/ThreadListItem.tsx",
  "src/lib/messaging/attachment-limits.ts",
  "src/lib/messaging/message-socket-client.ts",
  "src/lib/messaging/typing-label.ts",
  "src/lib/messaging/socket-types.ts",
  "src/hooks/useMessageSocket.ts",
  "src/hooks/useThreadRealtime.ts",
  "src/hooks/useUnreadRealtime.ts",
  "src/lib/messaging-api.ts",
  "src/lib/types/messaging.ts",
  "src/app/dashboard/messages/page.tsx",
  "src/app/host/messages/page.tsx",
];
for (const rel of required) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const composer = read("src/components/messaging/MessageComposer.tsx");
const bubble = read("src/components/messaging/MessageBubble.tsx");
const attBlock = read("src/components/messaging/MessageAttachmentBlock.tsx");
const inbox = read("src/components/messaging/MessagesInbox.tsx");
const threadList = read("src/components/messaging/ThreadListItem.tsx");
const limits = read("src/lib/messaging/attachment-limits.ts");
const api = read("src/lib/messaging-api.ts");
const types = read("src/lib/types/messaging.ts");
const socketClient = read("src/lib/messaging/message-socket-client.ts");
const socketStatus = read("src/components/messaging/MessagingSocketStatus.tsx");
const useSocket = read("src/hooks/useMessageSocket.ts");
const useRealtime = read("src/hooks/useThreadRealtime.ts");
const useUnread = read("src/hooks/useUnreadRealtime.ts");
const typingLabel = read("src/lib/messaging/typing-label.ts");
const socketTypes = read("src/lib/messaging/socket-types.ts");

// --- Composer: attach button ---
assert.match(composer, /export function MessageComposer/);
assert.match(composer, /aria-label="Attach file"/);
assert.match(composer, /PaperclipIcon|Attach/);
assert.match(composer, /type="file"/);
assert.match(composer, /ATTACHMENT_ACCEPT/);
assert.match(composer, /onUpload/);

// --- Allowed file preview ---
assert.match(composer, /URL\.createObjectURL/);
assert.match(composer, /previewUrl/);
assert.match(composer, /isImageContentType/);
assert.match(composer, /<img/);

// --- Unsupported file shows error ---
assert.match(composer, /validateAttachmentFile/);
assert.match(composer, /setError\(typeError\)/);
assert.match(composer, /role="alert"/);
assert.match(limits, /export function validateAttachmentFile/);
assert.match(limits, /Unsupported file type/);
assert.match(limits, /\.svg|\.zip|\.exe/);

// --- Upload progress displays ---
assert.match(composer, /progress/);
assert.match(composer, /role="progressbar"/);
assert.match(composer, /aria-valuenow=\{item\.progress\}/);
assert.match(composer, /onProgress/);
assert.match(composer, /status === "uploading"/);

// --- Remove attachment works ---
assert.match(composer, /removePending/);
assert.match(composer, /aria-label=\{`Remove \$\{item\.name\}`\}/);
assert.match(composer, /URL\.revokeObjectURL/);

// --- Send message with attachment ---
assert.match(composer, /onSend\(body\.trim\(\), readyIds\)/);
assert.match(composer, /readyIds/);
assert.match(composer, /attachmentIds/);
assert.match(inbox, /sendFanMessage|sendHostMessage/);
assert.match(inbox, /attachmentIds/);
assert.match(api, /export async function uploadMessageAttachment/);
assert.match(api, /export async function sendFanMessage/);
assert.match(api, /attachment_ids/);

// --- Image bubble renders ---
assert.match(bubble, /MessageAttachmentBlock/);
assert.match(bubble, /message\.attachments/);
assert.match(attBlock, /isImageContentType/);
assert.match(attBlock, /<img/);
assert.match(attBlock, /Open \$\{label\}|aria-label=\{`Open/);

// --- PDF/document bubble renders ---
assert.match(attBlock, /documentKindLabel/);
assert.match(attBlock, /Download/);
assert.match(limits, /export function documentKindLabel/);
assert.match(limits, /return "PDF"/);

// --- Unauthorized / request thread cannot upload ---
assert.match(inbox, /can_attach/);
assert.match(types, /can_attach\?:/);
assert.match(inbox, /onUpload=\{\s*\(/);
assert.match(
  inbox,
  /can_attach[\s\S]*\? async \(file, onProgress\)[\s\S]*: undefined/,
);
assert.match(inbox, /can_attach: false/);
assert.match(limits, /Not allowed in this thread/);
assert.match(composer, /Attachments unavailable|attachDisabled/);

// --- fan_fan: attachments only after accepted connection ---
assert.match(inbox, /onConnectionAccepted/);
assert.match(inbox, /thread_type === "fan_fan"/);
assert.match(useRealtime, /connection\.accepted|onConnectionAccepted/);
assert.match(types, /thread_type\?:/);
// Composer only mounts upload when can_attach is truthy (server gates Fan Connect).
assert.match(
  inbox,
  /activeDetail\.can_attach \?\?[\s\S]*!activeDetail\.is_request/,
);

// --- WebSocket updates thread in real time ---
assert.match(useSocket, /messageSocketClient\.ensureConnected/);
assert.match(useRealtime, /message\.created|onMessageCreated/);
assert.match(useRealtime, /thread\.updated|onThreadUpdated/);
assert.match(inbox, /onMessageCreated/);
assert.match(inbox, /setDetail/);
assert.match(socketClient, /WebSocket/);
assert.match(socketClient, /messagingWebSocketUrl/);
assert.match(api, /export function messagingWebSocketUrl|messagingWebSocketUrl/);
assert.match(api, /\/messages\/ws/);

// --- Typing indicator ---
assert.match(composer, /onTyping|notifyTyping/);
assert.match(inbox, /useTypingIndicator|peerTyping/);
assert.match(inbox, /formatTypingLabel/);
assert.match(typingLabel, /is typing/);
assert.match(socketClient, /typing\.start|typing\.stop/);

// --- Unread count updates live ---
assert.match(socketTypes, /thread\.unread_count_updated/);
assert.match(useUnread, /thread\.unread_count_updated/);
assert.match(useUnread, /unread_count/);
assert.match(inbox, /onThreadUpdated/);
assert.match(inbox, /unread:/);
assert.match(read("src/components/messaging/ThreadListItem.tsx"), /thread\.unread/);

// --- Reconnect state ---
assert.match(socketClient, /scheduleReconnect|reconnecting/);
assert.match(socketClient, /setStatus\("reconnecting"\)/);
assert.match(socketStatus, /status === "reconnecting"/);
assert.match(socketStatus, /Reconnecting/);
assert.match(socketStatus, /Connected/);
assert.match(socketStatus, /Offline/);
assert.match(inbox, /MessagingSocketStatus/);

// --- Mobile layout ---
assert.match(inbox, /hidden lg:flex|lg:flex-row/);
assert.match(inbox, /mobileListHidden|min-h-\[70vh\]/);
assert.match(composer, /hidden sm:inline/); // Attach label collapses on small screens

// --- Light / dark mode via brand tokens ---
for (const rel of [
  "src/components/messaging/MessageComposer.tsx",
  "src/components/messaging/MessageBubble.tsx",
  "src/components/messaging/MessageAttachmentBlock.tsx",
  "src/components/messaging/MessagesInbox.tsx",
  "src/components/messaging/MessagingSocketStatus.tsx",
  "src/components/messaging/ThreadListItem.tsx",
]) {
  assertThemeSafeTokens(rel, read(rel));
}
assert.match(composer, /dark:bg-surface-elevated|bg-card/);
assert.match(bubble, /dark:bg-surface-elevated/);
assert.match(inbox, /dark:bg-surface/);
assert.match(read("src/app/layout.tsx"), /ThemeProvider/);

// --- Executable client validation mirror (server remains authoritative) ---
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const ALLOWED_EXT = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".pdf",
  ".txt",
  ".csv",
  ".docx",
]);
const BLOCKED_EXT = new Set([".exe", ".svg", ".zip", ".html", ".js"]);

function validateMirror(file) {
  const i = file.name.lastIndexOf(".");
  const ext = i < 0 ? "" : file.name.slice(i).toLowerCase();
  if (ext && BLOCKED_EXT.has(ext)) return "Unsupported file type.";
  if (ext && !ALLOWED_EXT.has(ext)) return "Unsupported file type.";
  const mime = (file.type || "").split(";")[0].trim().toLowerCase();
  if (mime && !(IMAGE_TYPES.has(mime) || mime === "application/pdf" || mime === "text/plain")) {
    if (!ALLOWED_EXT.has(ext)) return "Unsupported file type.";
  }
  const limit = IMAGE_TYPES.has(mime) ? 5 * 1024 * 1024 : 10 * 1024 * 1024;
  if (file.size > limit) return `File too large (max ${limit}).`;
  if (file.size <= 0) return "Empty file.";
  return null;
}

assert.equal(
  validateMirror({ name: "a.png", type: "image/png", size: 1200 }),
  null,
);
assert.equal(
  validateMirror({ name: "note.pdf", type: "application/pdf", size: 2048 }),
  null,
);
assert.equal(
  validateMirror({ name: "evil.svg", type: "image/svg+xml", size: 100 }),
  "Unsupported file type.",
);
assert.equal(
  validateMirror({ name: "x.zip", type: "application/zip", size: 100 }),
  "Unsupported file type.",
);
assert.match(
  validateMirror({
    name: "huge.png",
    type: "image/png",
    size: 6 * 1024 * 1024,
  }) || "",
  /too large/i,
);

// Limits source stays aligned with smoke defaults
assert.match(limits, /ATTACHMENT_MAX_IMAGE_BYTES = 5 \* 1024 \* 1024/);
assert.match(limits, /ATTACHMENT_MAX_DOC_BYTES = 10 \* 1024 \* 1024/);
assert.match(limits, /ATTACHMENT_MAX_COUNT = 4/);

// --- Chat features: timestamps, reply/edit/pin/star ---
assert.ok(exists("src/lib/format-message-time.ts"));
assert.ok(exists("src/components/messaging/MessageActionMenu.tsx"));
assert.ok(exists("src/components/messaging/MessageTimestamp.tsx"));
assert.ok(exists("src/components/messaging/MessageStatus.tsx"));
assert.ok(exists("src/components/messaging/MessageMeta.tsx"));
assert.ok(exists("src/components/messaging/QuotedMessage.tsx"));
assert.ok(exists("src/components/messaging/ReplyPreview.tsx"));
assert.ok(exists("src/components/messaging/MessageEditComposer.tsx"));
assert.ok(exists("src/components/messaging/DateSeparator.tsx"));
assert.ok(exists("src/components/messaging/StarredMessagesList.tsx"));
assert.ok(exists("src/components/messaging/PinnedMessagesBar.tsx"));
assert.ok(exists("src/components/messaging/ThreadSearch.tsx"));
const timeFmt = read("src/lib/format-message-time.ts");
const actionMenu = read("src/components/messaging/MessageActionMenu.tsx");
const timestamp = read("src/components/messaging/MessageTimestamp.tsx");
const meta = read("src/components/messaging/MessageMeta.tsx");
assert.match(timeFmt, /export function formatMessageSentAt/);
assert.match(timeFmt, /export function formatThreadListTime/);
assert.match(timeFmt, /export function formatMessageDaySeparator/);
assert.match(timeFmt, /Yesterday/);
assert.match(timestamp, /formatMessageSentAt/);
assert.match(timestamp, /text-\[10px\]/);
assert.match(meta, /MessageTimestamp|MessageStatus/);
assert.match(bubble, /MessageMeta|MessageTimestamp|QuotedMessage/);
assert.match(bubble, /Edited|Delivered|Read|Sent|Failed|MessageStatus|MessageMeta/);
assert.ok(exists("src/lib/messaging/message-status.ts"));
const msgStatus = read("src/lib/messaging/message-status.ts");
assert.match(msgStatus, /formatOwnDeliveryStatus/);
assert.match(msgStatus, /Read/);
assert.match(msgStatus, /Delivered/);
assert.match(msgStatus, /Failed/);
assert.match(inbox, /peerReadAt|client_failed|local-failed/);
assert.match(threadList, /last_message_preview|unread/);
assert.ok(exists("src/components/messaging/ThreadMessageSearch.tsx"));
assert.match(inbox, /ThreadSearch|ThreadMessageSearch|searchThreadMessages/);
assert.match(api, /threads\/.*\/search|searchThreadMessages/);
assert.match(
  read("src/components/messaging/ThreadMessageSearch.tsx"),
  /Search in conversation|Starred|Pinned|Files/,
);
assert.match(
  read("src/components/messaging/PinnedMessagesBanner.tsx"),
  /Hide|All/,
);
assert.match(bubble, /QuotedMessage|reply_to|onReplyTap/);
assert.match(types, /reply_message_id|reply_is_unavailable|reply_body_preview/);
assert.match(actionMenu, /Reply/);
assert.match(actionMenu, /Edit/);
assert.match(actionMenu, /Pin/);
assert.match(actionMenu, /Star/);
assert.match(actionMenu, /Copy text/);
assert.match(actionMenu, /Report/);
assert.match(actionMenu, /Block user/);
assert.match(actionMenu, /Delete for me|delete_for_me/);
assert.match(api, /deleteMessageForMe|\/delete/);
assert.match(types, /deleted_for_me/);
assert.match(bubble, /deleted_for_me|Message deleted/);
assert.match(actionMenu, /group-hover:opacity|LONG_PRESS|long.?press|opacity-0/);
assert.match(bubble, /LONG_PRESS|longPress|onPointerDown|onContextMenu/);
assert.match(inbox, /canReport|canBlock|action === "report"|action === "block"/);
assert.match(composer, /editTarget|MessageEditComposer/);
assert.match(composer, /replyTo|ReplyPreview/);
assert.match(
  read("src/components/messaging/MessageEditComposer.tsx"),
  /Editing message/,
);
assert.match(
  read("src/components/messaging/ReplyPreview.tsx"),
  /Replying to/,
);
assert.match(inbox, /pinned_messages|PinnedMessagesBar|PinnedMessagesBanner/);
assert.ok(exists("src/components/messaging/PinnedMessagesBanner.tsx"));
assert.match(api, /\/pin|\/unpin|threads\/.*\/pins/);
assert.match(inbox, /Starred messages|starred|StarredMessagesList/);
assert.match(inbox, /searchParams\.get\("m"\)|focusMessageId/);
assert.match(
  read("src/components/messaging/StarredMessagesList.tsx"),
  /\?m=/,
);
assert.match(inbox, /DateSeparator|formatMessageDaySeparator/);
assert.match(inbox, /handleMessageAction|onAction/);
assert.match(api, /editMessage|pinMessage|starMessage|listStarredMessages/);
assert.match(api, /\/star|\/unstar/);
assert.match(api, /method: "PATCH"/);
assert.match(api, /\$\{base\}\/\$\{encodeURIComponent\(messageId\)\}/);
assert.match(types, /edited_at|reply_to|is_pinned|is_starred/);
assert.match(socketTypes, /message\.pinned|message\.unpinned/);
assert.match(useRealtime, /onMessagePinned|message\.pinned/);
assert.match(inbox, /Pàdéyá/);
assert.doesNotMatch(inbox, /Padéyá|Pàdéyé|\bPadeya\b/);
assert.doesNotMatch(bubble, /Padéyá|Pàdéyé|\bPadeya\b/);
assert.doesNotMatch(composer, /Padéyá|Pàdéyé|\bPadeya\b/);

// Deterministic timestamp helper checks (inline mirror of calendar rules)
function dayDiff(a, b) {
  const sa = new Date(a.getFullYear(), a.getMonth(), a.getDate());
  const sb = new Date(b.getFullYear(), b.getMonth(), b.getDate());
  return Math.round((sa - sb) / 86400000);
}
const fixedNow = new Date(2026, 6, 18, 14, 35, 0); // Jul 18, 2026 2:35 PM local
assert.equal(dayDiff(fixedNow, new Date(2026, 6, 18, 10, 0, 0)), 0);
assert.equal(dayDiff(fixedNow, new Date(2026, 6, 17, 10, 0, 0)), 1);
assert.ok(dayDiff(fixedNow, new Date(2025, 0, 12, 10, 0, 0)) > 1);

// Delivery / read status priority (mirror of message-status.ts)
function deliveryLabel({ status, createdAt, peerReadAt, clientFailed }) {
  if (clientFailed || status === "failed") return "Failed";
  if (
    peerReadAt &&
    createdAt &&
    new Date(peerReadAt).getTime() >= new Date(createdAt).getTime()
  ) {
    return "Read";
  }
  if (status === "delivered") return "Delivered";
  if (status === "hidden" || status === "deleted") return null;
  return "Sent";
}
assert.equal(
  deliveryLabel({
    status: "delivered",
    createdAt: "2026-07-18T10:00:00.000Z",
    peerReadAt: "2026-07-18T11:00:00.000Z",
  }),
  "Read",
);
assert.equal(
  deliveryLabel({
    status: "delivered",
    createdAt: "2026-07-18T12:00:00.000Z",
    peerReadAt: "2026-07-18T11:00:00.000Z",
  }),
  "Delivered",
);
assert.equal(deliveryLabel({ status: "sent" }), "Sent");
assert.equal(deliveryLabel({ status: "sent", clientFailed: true }), "Failed");

console.log("messaging-attachments-smoke: ok");
