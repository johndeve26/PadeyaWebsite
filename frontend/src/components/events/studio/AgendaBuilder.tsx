"use client";

import {
  Button,
  ConfirmAction,
  EmptyState,
  Input,
  Select,
  Textarea,
} from "@/components/ui";

import {
  AGENDA_ITEM_TYPES,
  agendaEndAfterStartError,
  newAgendaItem,
  normalizeAgendaType,
  type StudioAgendaItem,
} from "./agenda-utils";
import { StudioItemCard, StudioMicrocopy } from "./studio-ui";

function moveItem(
  list: StudioAgendaItem[],
  from: number,
  to: number,
): StudioAgendaItem[] {
  if (to < 0 || to >= list.length) return list;
  const next = [...list];
  const [row] = next.splice(from, 1);
  next.splice(to, 0, row);
  return next.map((item, index) => ({ ...item, sort_order: index }));
}

export function AgendaBuilder({
  items,
  onChange,
}: {
  items: StudioAgendaItem[];
  onChange: (items: StudioAgendaItem[]) => void;
}) {
  function update(localId: string, patch: Partial<StudioAgendaItem>) {
    const nextPatch =
      patch.type !== undefined
        ? { ...patch, type: normalizeAgendaType(patch.type) }
        : patch;
    onChange(
      items.map((item) =>
        item.localId === localId ? { ...item, ...nextPatch } : item,
      ),
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-semibold text-foreground">Agenda</p>
        <StudioMicrocopy>
          Optional run-of-show for guests — doors, sets, speakers, breaks. Skip
          if the night is open-format. Reorder with Move up / Move down.
        </StudioMicrocopy>
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="No agenda yet"
          description="Add doors open, performances, speakers, or after-party beats."
          action={
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                onChange([
                  newAgendaItem({
                    title: "Doors Open",
                    type: "doors_open",
                    sort_order: 0,
                  }),
                ])
              }
            >
              Add first agenda item
            </Button>
          }
        />
      ) : null}
      {items.map((item, index) => {
        const timeError = agendaEndAfterStartError(
          item.start_time,
          item.end_time,
        );
        return (
          <StudioItemCard
            key={item.localId}
            title={`Item ${index + 1}${item.title.trim() ? ` · ${item.title.trim()}` : ""}`}
            actions={
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={index === 0}
                  onClick={() => onChange(moveItem(items, index, index - 1))}
                >
                  Move up
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={index >= items.length - 1}
                  onClick={() => onChange(moveItem(items, index, index + 1))}
                >
                  Move down
                </Button>
                <ConfirmAction
                  label="Remove"
                  title="Remove this agenda item?"
                  description="It is deleted from the event when you save. Guests will no longer see this block."
                  confirmLabel="Remove"
                  tone="danger"
                  variant="ghost"
                  onConfirm={() =>
                    onChange(
                      items.filter((row) => row.localId !== item.localId),
                    )
                  }
                />
              </>
            }
          >
            <Input
              label="Title"
              required
              hint="Short name guests will see (e.g. “Doors Open”, “Headliner set”)."
              value={item.title}
              onChange={(e) => update(item.localId, { title: e.target.value })}
            />
            <Select
              label="Type"
              hint="Category for the agenda block — helps guests scan the timeline."
              value={normalizeAgendaType(item.type)}
              onChange={(e) => update(item.localId, { type: e.target.value })}
            >
              {AGENDA_ITEM_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </Select>
            <Textarea
              label="Description"
              rows={2}
              hint="Optional detail (who is on stage, what happens in this slot)."
              value={item.description ?? ""}
              onChange={(e) =>
                update(item.localId, { description: e.target.value })
              }
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Starts"
                type="datetime-local"
                hint="When this block begins."
                value={item.start_time ?? ""}
                onChange={(e) =>
                  update(item.localId, { start_time: e.target.value })
                }
              />
              <Input
                label="Ends"
                type="datetime-local"
                hint="When this block ends (optional)."
                error={timeError ?? undefined}
                value={item.end_time ?? ""}
                onChange={(e) =>
                  update(item.localId, { end_time: e.target.value })
                }
              />
            </div>
          </StudioItemCard>
        );
      })}
      {items.length > 0 ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() =>
            onChange([...items, newAgendaItem({ sort_order: items.length })])
          }
        >
          Add agenda item
        </Button>
      ) : null}
    </div>
  );
}

export {
  AGENDA_ITEM_TYPES,
  agendaEndAfterStartError,
  newAgendaItem,
  toStudioAgendaItems,
  type StudioAgendaItem,
} from "./agenda-utils";
