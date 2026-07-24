"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Alert, Button, Input, Textarea, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import {
  createBlogComment,
  fetchBlogComments,
  replyToBlogComment,
  updateBlogComment,
  withdrawBlogComment,
  type BlogComment,
} from "@/lib/blog-api";

/** Mirrors backend GUEST_COMMENTS_ALLOWED — guest replies follow guest comment policy. */
const GUEST_REPLIES_ENABLED = true;
const REPLY_COLLAPSE_THRESHOLD = 3;

function formatCommentDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

function countVisibleComments(comments: BlogComment[]): number {
  return comments.reduce(
    (sum, c) => sum + 1 + (c.replies?.length ?? 0),
    0,
  );
}

function updateCommentInTree(
  comments: BlogComment[],
  id: string,
  updater: (c: BlogComment) => BlogComment,
): BlogComment[] {
  return comments.map((c) => {
    if (c.id === id) return updater(c);
    if (c.replies?.length) {
      return {
        ...c,
        replies: c.replies.map((r) => (r.id === id ? updater(r) : r)),
      };
    }
    return c;
  });
}

function removeCommentFromTree(
  comments: BlogComment[],
  id: string,
): BlogComment[] {
  return comments
    .filter((c) => c.id !== id)
    .map((c) => ({
      ...c,
      replies: (c.replies ?? []).filter((r) => r.id !== id),
      reply_count:
        (c.replies ?? []).some((r) => r.id === id)
          ? Math.max(0, (c.reply_count ?? c.replies?.length ?? 1) - 1)
          : c.reply_count,
    }));
}

function insertReplyUnderParent(
  comments: BlogComment[],
  parentId: string,
  reply: BlogComment,
): BlogComment[] {
  return comments.map((c) => {
    if (c.id !== parentId) return c;
    const replies = [...(c.replies ?? []), reply];
    return {
      ...c,
      replies,
      reply_count: replies.length,
    };
  });
}

function CommentAuthor({ comment }: { comment: BlogComment }) {
  if (comment.passport_path) {
    return (
      <Link
        href={comment.passport_path}
        className="font-semibold text-heading transition-colors hover:text-primary-text"
      >
        {comment.display_name}
      </Link>
    );
  }
  return (
    <span className="font-semibold text-heading">{comment.display_name}</span>
  );
}

function AuthorBadge({ comment }: { comment: BlogComment }) {
  if (!comment.author_badge) return null;
  return (
    <span className="rounded-[var(--radius-sm)] bg-surface-muted px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-heading">
      {comment.author_badge}
    </span>
  );
}

function EditedLabel({ comment }: { comment: BlogComment }) {
  if (!comment.is_edited) return null;
  if (comment.edited_by_moderator) {
    return (
      <span className="text-xs text-muted-foreground">Edited by moderator</span>
    );
  }
  if (comment.edited_at) {
    return (
      <span className="text-xs text-muted-foreground">
        Edited on {formatCommentDate(comment.edited_at)}
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">Edited</span>;
}

function replyCountLabel(count: number): string {
  return count === 1 ? "1 reply" : `${count} replies`;
}

export function BlogComments({ postSlug }: { postSlug: string }) {
  const { user, loading: authLoading } = useAuth();
  const toast = useToast();
  const isLoggedIn = Boolean(user);
  const isStaffEditor = userHasPermission(
    user,
    "admin.blog.comments.edit_any",
    "admin.blog.comments.moderate",
    "admin.blog.edit",
  );
  const canAttemptReply =
    isLoggedIn || (!authLoading && GUEST_REPLIES_ENABLED);
  const loginHref = `/login?next=${encodeURIComponent(`/blog/${postSlug}`)}`;

  const [comments, setComments] = useState<BlogComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [guestName, setGuestName] = useState("");
  const [website, setWebsite] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submittedNotice, setSubmittedNotice] = useState(false);
  const [withdrawingId, setWithdrawingId] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [editReason, setEditReason] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const [replyingToId, setReplyingToId] = useState<string | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [replyGuestName, setReplyGuestName] = useState("");
  const [replyWebsite, setReplyWebsite] = useState("");
  const [replyError, setReplyError] = useState<string | null>(null);
  const [replyNotice, setReplyNotice] = useState<string | null>(null);
  const [replyingSaving, setReplyingSaving] = useState(false);
  const [expandedReplies, setExpandedReplies] = useState<
    Record<string, boolean>
  >({});

  const load = useCallback(async () => {
    setLoadError(null);
    setLoading(true);
    try {
      const rows = await fetchBlogComments(postSlug);
      setComments(rows);
    } catch {
      setComments([]);
      setLoadError("Couldn’t load comments. Please refresh and try again.");
    } finally {
      setLoading(false);
    }
  }, [postSlug]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (user?.full_name) {
      setGuestName(user.full_name);
      setReplyGuestName(user.full_name);
    }
  }, [user?.full_name]);

  function startEdit(comment: BlogComment) {
    setEditingId(comment.id);
    setEditBody(comment.body);
    setEditReason("");
    setEditError(null);
    setReplyingToId(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditBody("");
    setEditReason("");
    setEditError(null);
  }

  function startReply(comment: BlogComment) {
    if (!canAttemptReply) return;
    setReplyingToId(comment.id);
    setReplyBody("");
    setReplyError(null);
    setReplyNotice(null);
    setReplyWebsite("");
    setEditingId(null);
  }

  function cancelReply() {
    setReplyingToId(null);
    setReplyBody("");
    setReplyError(null);
    setReplyNotice(null);
    setReplyWebsite("");
  }

  async function saveEdit(comment: BlogComment) {
    const trimmed = editBody.trim();
    if (trimmed.length < 2) {
      setEditError("Comment must be at least 2 characters.");
      return;
    }
    setSavingId(comment.id);
    setEditError(null);
    try {
      const updated = await updateBlogComment(comment.id, {
        body: trimmed,
        edit_reason:
          isStaffEditor && !comment.is_mine
            ? editReason.trim() || undefined
            : isStaffEditor && editReason.trim()
              ? editReason.trim()
              : undefined,
      });
      setComments((prev) =>
        updateCommentInTree(prev, comment.id, (c) => ({
          ...c,
          ...updated,
          replies: c.replies,
        })),
      );
      cancelEdit();
      toast.push({ tone: "success", title: "Comment updated" });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not save changes. Please try again.";
      setEditError(message);
    } finally {
      setSavingId(null);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmittedNotice(false);

    const trimmed = body.trim();
    if (trimmed.length < 2) {
      setError("Comment must be at least 2 characters.");
      return;
    }

    if (!isLoggedIn && guestName.trim().length < 2) {
      setError("Please enter your name.");
      return;
    }

    setSubmitting(true);
    try {
      await createBlogComment(postSlug, {
        body: trimmed,
        guest_name: isLoggedIn ? undefined : guestName.trim(),
        website,
      });
      setBody("");
      setSubmittedNotice(true);
      toast.push({
        tone: "success",
        title: "Comment submitted",
        description: "It may be reviewed before appearing.",
      });
      await load();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not post your comment. Please try again.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function onPostReply(parent: BlogComment) {
    const trimmed = replyBody.trim();
    if (trimmed.length < 2) {
      setReplyError("Reply must be at least 2 characters.");
      return;
    }
    if (!isLoggedIn && replyGuestName.trim().length < 2) {
      setReplyError("Please enter your name.");
      return;
    }

    setReplyingSaving(true);
    setReplyError(null);
    setReplyNotice(null);
    try {
      const created = await replyToBlogComment(parent.id, {
        body: trimmed,
        guest_name: isLoggedIn ? undefined : replyGuestName.trim(),
        website: replyWebsite,
      });
      setComments((prev) => insertReplyUnderParent(prev, parent.id, created));
      cancelReply();
      toast.push({ tone: "success", title: "Reply posted" });
      setReplyNotice(null);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not post your reply. Please try again.";
      setReplyError(message);
    } finally {
      setReplyingSaving(false);
    }
  }

  async function onWithdraw(commentId: string) {
    setWithdrawingId(commentId);
    try {
      await withdrawBlogComment(commentId);
      setComments((prev) => removeCommentFromTree(prev, commentId));
      if (editingId === commentId) cancelEdit();
      if (replyingToId === commentId) cancelReply();
      toast.push({ tone: "success", title: "Comment removed" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Could not remove comment",
        description:
          err instanceof ApiError ? err.message : "Please try again.",
      });
    } finally {
      setWithdrawingId(null);
    }
  }

  function renderEditForm(comment: BlogComment) {
    return (
      <div className="mt-3 space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/40 p-3 sm:p-4">
        <Textarea
          label={comment.depth === 1 ? "Edit reply" : "Edit comment"}
          value={editBody}
          onChange={(e) => setEditBody(e.target.value)}
          rows={3}
          maxLength={2000}
          disabled={savingId === comment.id}
        />
        {isStaffEditor ? (
          <Input
            label="Edit reason (optional, internal)"
            value={editReason}
            onChange={(e) => setEditReason(e.target.value)}
            maxLength={500}
            hint={
              comment.is_mine
                ? "Add a reason to mark this as a moderator edit"
                : "Stored for moderation audit — not shown publicly"
            }
            disabled={savingId === comment.id}
          />
        ) : null}
        {editError ? <Alert tone="danger">{editError}</Alert> : null}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="primary"
            disabled={savingId === comment.id}
            onClick={() => void saveEdit(comment)}
          >
            {savingId === comment.id ? "Saving…" : "Save changes"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={savingId === comment.id}
            onClick={cancelEdit}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  function renderReplyForm(parent: BlogComment) {
    return (
      <div className="relative mt-3 space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-muted/30 p-3 sm:p-4">
        {!isLoggedIn ? (
          <Input
            label="Name"
            value={replyGuestName}
            onChange={(e) => setReplyGuestName(e.target.value)}
            autoComplete="name"
            required
            maxLength={120}
            disabled={replyingSaving}
          />
        ) : (
          <p className="text-sm text-foreground/70">
            Replying as{" "}
            <span className="font-semibold text-heading">
              {user?.full_name || "Member"}
            </span>
          </p>
        )}
        <div
          className="absolute -left-[9999px] h-0 w-0 overflow-hidden opacity-0"
          aria-hidden
        >
          <label htmlFor={`blog-reply-website-${parent.id}`}>Website</label>
          <input
            id={`blog-reply-website-${parent.id}`}
            tabIndex={-1}
            autoComplete="off"
            value={replyWebsite}
            onChange={(e) => setReplyWebsite(e.target.value)}
          />
        </div>
        <Textarea
          label="Your reply"
          value={replyBody}
          onChange={(e) => setReplyBody(e.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="Write a reply…"
          disabled={replyingSaving}
        />
        {replyError ? <Alert tone="danger">{replyError}</Alert> : null}
        {replyNotice ? <Alert tone="success">{replyNotice}</Alert> : null}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="primary"
            disabled={replyingSaving}
            onClick={() => void onPostReply(parent)}
          >
            {replyingSaving ? "Posting…" : "Post reply"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={replyingSaving}
            onClick={cancelReply}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  function renderCommentActions(
    comment: BlogComment,
    { isReply }: { isReply: boolean },
  ) {
    const canEdit = Boolean(comment.can_edit);
    const isEditing = editingId === comment.id;

    return (
      <div className="flex flex-wrap items-center gap-1">
        {canEdit && !isEditing ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => startEdit(comment)}
          >
            Edit
          </Button>
        ) : null}
        {!isReply ? (
          canAttemptReply && comment.can_reply !== false ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => startReply(comment)}
              disabled={replyingToId === comment.id}
            >
              Reply
            </Button>
          ) : !isLoggedIn && !GUEST_REPLIES_ENABLED ? (
            <Link
              href={loginHref}
              className="px-2 py-1 text-xs font-semibold text-primary-text hover:underline"
            >
              Sign in to reply
            </Link>
          ) : comment.can_reply === false && isLoggedIn ? (
            <span className="px-2 py-1 text-xs text-muted-foreground">
              You cannot reply to this comment
            </span>
          ) : null
        ) : null}
        {comment.is_mine ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={withdrawingId === comment.id}
            onClick={() => void onWithdraw(comment.id)}
          >
            {withdrawingId === comment.id ? "Removing…" : "Remove"}
          </Button>
        ) : null}
      </div>
    );
  }

  function renderMeta(comment: BlogComment) {
    return (
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
        <CommentAuthor comment={comment} />
        <AuthorBadge comment={comment} />
        {comment.is_guest ? (
          <span className="text-xs text-muted-foreground">Guest</span>
        ) : null}
        <span aria-hidden className="text-border-strong">
          ·
        </span>
        <time
          dateTime={comment.created_at}
          className="text-xs text-muted-foreground"
        >
          {formatCommentDate(comment.created_at)}
        </time>
        {comment.is_edited ? (
          <>
            <span aria-hidden className="text-border-strong">
              ·
            </span>
            <EditedLabel comment={comment} />
          </>
        ) : null}
      </div>
    );
  }

  function renderReplyItem(reply: BlogComment) {
    const isEditing = editingId === reply.id;
    return (
      <li key={reply.id} className="pt-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          {renderMeta(reply)}
          {renderCommentActions(reply, { isReply: true })}
        </div>
        {isEditing ? (
          renderEditForm(reply)
        ) : (
          <p className="mt-1.5 whitespace-pre-wrap text-pretty text-[14px] leading-relaxed text-foreground/85">
            {reply.body}
          </p>
        )}
      </li>
    );
  }

  function renderThread(comment: BlogComment) {
    const isEditing = editingId === comment.id;
    const isReplying = replyingToId === comment.id;
    const replies = comment.replies ?? [];
    const replyCount = replies.length;
    const expanded = expandedReplies[comment.id] ?? false;
    const shouldCollapse = replyCount > REPLY_COLLAPSE_THRESHOLD;
    const visibleReplies =
      shouldCollapse && !expanded
        ? replies.slice(-REPLY_COLLAPSE_THRESHOLD)
        : replies;
    const hiddenCount = shouldCollapse && !expanded
      ? replyCount - REPLY_COLLAPSE_THRESHOLD
      : 0;

    return (
      <li
        key={comment.id}
        className="border-t border-border pt-5 first:border-t-0 first:pt-0"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          {renderMeta(comment)}
          {renderCommentActions(comment, { isReply: false })}
        </div>

        {isEditing ? (
          renderEditForm(comment)
        ) : (
          <p className="mt-2 whitespace-pre-wrap text-pretty text-[15px] leading-relaxed text-foreground/85">
            {comment.body}
          </p>
        )}

        {isReplying ? renderReplyForm(comment) : null}

        {replyCount > 0 ? (
          <div className="mt-3 border-l-2 border-border pl-4 sm:pl-5">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {replyCountLabel(replyCount)}
              </p>
              {shouldCollapse ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    setExpandedReplies((prev) => ({
                      ...prev,
                      [comment.id]: !expanded,
                    }))
                  }
                >
                  {expanded
                    ? "Collapse replies"
                    : `Show ${hiddenCount} more`}
                </Button>
              ) : null}
            </div>
            <ul className="space-y-1">{visibleReplies.map(renderReplyItem)}</ul>
          </div>
        ) : null}
      </li>
    );
  }

  const totalCount = countVisibleComments(comments);

  return (
    <section
      className="space-y-6 border-t border-border pt-12"
      aria-labelledby="blog-comments-heading"
    >
      <div className="max-w-2xl">
        <p className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.2em] text-heading">
          <span
            aria-hidden
            className="inline-block h-[3px] w-7 shrink-0 rounded-[1px] bg-primary"
          />
          Discussion
        </p>
        <h2
          id="blog-comments-heading"
          className="mt-2 font-display text-2xl font-extrabold tracking-tight text-heading sm:text-3xl"
        >
          Comments
          {!loading && !loadError ? (
            <span className="ml-2 text-lg font-semibold text-muted-foreground">
              ({totalCount})
            </span>
          ) : null}
        </h2>
        <p className="mt-2 text-sm text-foreground/70">
          Guests need only a display name. Keep it respectful — spam and abuse
          are removed.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="relative max-w-2xl space-y-3.5 rounded-[var(--radius-lg)] border border-border bg-card/70 p-4 shadow-[var(--shadow-soft)] sm:p-5 dark:bg-surface-elevated"
      >
        {!authLoading && !isLoggedIn ? (
          <Input
            label="Name"
            name="guest_name"
            value={guestName}
            onChange={(e) => setGuestName(e.target.value)}
            autoComplete="name"
            required
            maxLength={120}
          />
        ) : null}

        {isLoggedIn ? (
          <p className="text-sm text-foreground/70">
            Commenting as{" "}
            <span className="font-semibold text-heading">
              {user?.full_name || "Member"}
            </span>
          </p>
        ) : null}

        <div
          className="absolute -left-[9999px] h-0 w-0 overflow-hidden opacity-0"
          aria-hidden
        >
          <label htmlFor="blog-comment-website">Website</label>
          <input
            id="blog-comment-website"
            tabIndex={-1}
            autoComplete="off"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />
        </div>

        <Textarea
          label="Your comment"
          name="body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={3}
          required
          maxLength={2000}
          placeholder="What stood out to you?"
        />

        <p className="text-xs leading-relaxed text-muted-foreground">
          Don&apos;t share private contact details in the comment body.
        </p>

        {error ? <Alert tone="danger">{error}</Alert> : null}
        {submittedNotice ? (
          <Alert tone="success" title="Thanks for commenting">
            Your comment was submitted and may be reviewed before it appears.
          </Alert>
        ) : null}

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Button
            type="submit"
            variant="primary"
            disabled={submitting || authLoading}
          >
            {submitting ? "Submitting…" : "Post comment"}
          </Button>
          {!isLoggedIn && !authLoading ? (
            <p className="text-xs text-muted-foreground">
              <Link
                href={loginHref}
                className="font-semibold text-primary-text hover:underline"
              >
                Sign in
              </Link>{" "}
              to comment as yourself.
            </p>
          ) : null}
        </div>
      </form>

      <div className="max-w-2xl space-y-5">
        {loading ? (
          <div
            className="space-y-4"
            aria-busy="true"
            aria-label="Loading comments"
          >
            {[0, 1].map((i) => (
              <div
                key={i}
                className="animate-pulse space-y-2 border-t border-border pt-5 first:border-t-0 first:pt-0"
              >
                <div className="h-3 w-40 rounded bg-surface-muted" />
                <div className="h-3 w-full rounded bg-surface-muted" />
                <div className="h-3 w-[80%] rounded bg-surface-muted" />
              </div>
            ))}
          </div>
        ) : loadError ? (
          <Alert
            tone="warning"
            title="Comments unavailable"
            action={
              <Button size="sm" variant="secondary" onClick={() => void load()}>
                Retry
              </Button>
            }
          >
            {loadError}
          </Alert>
        ) : comments.length === 0 ? (
          <p className="rounded-[var(--radius-md)] border border-dashed border-border bg-surface-muted/40 px-4 py-6 text-sm text-muted-foreground">
            No comments yet — be the first (after review).
          </p>
        ) : (
          <ul className="space-y-5">{comments.map(renderThread)}</ul>
        )}
      </div>
    </section>
  );
}
