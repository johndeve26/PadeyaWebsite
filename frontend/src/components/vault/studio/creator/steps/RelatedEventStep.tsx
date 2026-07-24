"use client";

import type { VaultItemEditorValues } from "@/components/vault/studio/VaultItemEditor";
import { Card, Select } from "@/components/ui";
import { VAULT_LEGACY_BLOCK_DESCRIPTION } from "@/lib/vault-copy";
import type { EventItem } from "@/lib/types/events";

type MemoryOption = { id: string; label: string };

type Props = {
  values: VaultItemEditorValues;
  onChange: (next: VaultItemEditorValues) => void;
  events: EventItem[];
  memories: MemoryOption[];
};

export function RelatedEventStep({
  values,
  onChange,
  events,
  memories,
}: Props) {
  const relatedEvent = events.find((e) => e.id === values.related_event_id);

  return (
    <div className="space-y-5">
      <div className="space-y-1">
        <h2 className="text-xl font-extrabold text-foreground">Related Event</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Connect this drop to an event or Event Memory so it surfaces with your
          Legacy story.
        </p>
      </div>

      <Select
        label="Related event"
        value={values.related_event_id}
        onChange={(e) =>
          onChange({
            ...values,
            related_event_id: e.target.value,
            related_memory_id: "",
          })
        }
        hint="Optional. Ticket-scoped access can also use a required event on the Access step."
      >
        <option value="">None</option>
        {events.map((event) => (
          <option key={event.id} value={event.id}>
            {event.title}
          </option>
        ))}
      </Select>

      <Select
        label="Related memory"
        value={values.related_memory_id}
        onChange={(e) =>
          onChange({ ...values, related_memory_id: e.target.value })
        }
        hint={
          memories.length === 0
            ? "No Event Memories found for the selected event yet."
            : "Must belong to the related event when both are set."
        }
      >
        <option value="">None</option>
        {memories.map((memory) => (
          <option key={memory.id} value={memory.id}>
            {memory.label}
          </option>
        ))}
      </Select>

      <Card className="space-y-3 bg-muted/60">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          How this connects to Legacy
        </p>
        <p className="text-sm leading-relaxed text-foreground">
          {VAULT_LEGACY_BLOCK_DESCRIPTION}
        </p>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>
            Published drops can appear in the Legacy{" "}
            <span className="font-semibold text-foreground">Vault preview</span>{" "}
            block.
          </li>
          <li>
            On the next step you can pin this drop as the featured Vault item.
          </li>
          {relatedEvent ? (
            <li>
              Linked to{" "}
              <span className="font-semibold text-foreground">
                {relatedEvent.title}
              </span>
              — fans discover it beside that event’s story.
            </li>
          ) : (
            <li>
              No related event yet — you can still publish a standalone exclusive
              drop.
            </li>
          )}
        </ul>
      </Card>

      <label className="flex items-start gap-3 rounded-[var(--radius-md)] border border-border bg-surface-inset px-4 py-3 text-sm">
        <input
          type="checkbox"
          className="mt-0.5 accent-accent"
          checked={values.feature_on_legacy}
          onChange={(e) =>
            onChange({ ...values, feature_on_legacy: e.target.checked })
          }
        />
        <span>
          <span className="font-semibold text-foreground">
            Feature on Legacy Vault preview
          </span>
          <span className="mt-0.5 block text-muted-foreground">
            Pins this drop as the featured Vault item on your public Legacy Page
            after save.
          </span>
        </span>
      </label>
    </div>
  );
}
