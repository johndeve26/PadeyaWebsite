"use client";

import {
  type FormEvent,
  type KeyboardEvent,
  useId,
  useState,
} from "react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

export function AssistantComposer({
  disabled,
  streaming,
  onSend,
  onStop,
}: {
  disabled?: boolean;
  streaming: boolean;
  onSend: (message: string) => void;
  onStop: () => void;
}) {
  const inputId = useId();
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled || streaming) return;
    onSend(trimmed);
    setValue("");
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="shrink-0 border-t border-border px-4 py-3 sm:px-5"
    >
      <label htmlFor={inputId} className="sr-only">
        Message Ask Pàdéyá
      </label>
      <div className="flex items-end gap-2">
        <textarea
          id={inputId}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder="Ask anything…"
          maxLength={4000}
          className={cn(
            "min-h-11 max-h-32 flex-1 resize-y rounded-[var(--radius-md)] border border-border bg-background px-3 py-2.5 text-sm text-foreground shadow-[var(--shadow-soft)] placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:cursor-not-allowed disabled:opacity-55",
          )}
        />
        {streaming ? (
          <Button
            type="button"
            size="md"
            variant="secondary"
            aria-label="Stop generating"
            onClick={onStop}
          >
            Stop
          </Button>
        ) : (
          <Button
            type="submit"
            size="md"
            variant="primary"
            aria-label="Send message"
            disabled={disabled || !value.trim()}
          >
            Send
          </Button>
        )}
      </div>
    </form>
  );
}
