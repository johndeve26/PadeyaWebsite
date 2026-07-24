"use client";

import { useState } from "react";

import { Button, Textarea, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { submitHelpFeedback } from "@/lib/knowledge-base/api";

export function HelpFeedback({ articleId }: { articleId: string }) {
  const toast = useToast();
  const [done, setDone] = useState<"yes" | "no" | null>(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(isHelpful: boolean) {
    setBusy(true);
    try {
      await submitHelpFeedback(articleId, {
        is_helpful: isHelpful,
        comment: comment.trim() || undefined,
      });
      setDone(isHelpful ? "yes" : "no");
      toast.push({ tone: "success", title: "Thanks for the feedback" });
    } catch (e) {
      toast.push({
        tone: "danger",
        title: e instanceof ApiError ? e.message : "Could not send feedback",
      });
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <p className="text-sm font-medium text-muted-foreground">
        {done === "yes"
          ? "Glad this helped."
          : "Thanks — we’ll use that to improve this guide."}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold text-heading">Was this helpful?</p>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void send(true)}
        >
          Yes
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void send(false)}
        >
          No
        </Button>
      </div>
      <Textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optional comment (max 500 characters)"
        rows={2}
        maxLength={500}
        className="max-w-lg"
      />
    </div>
  );
}
