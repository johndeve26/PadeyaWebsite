"use client";

import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import {
  Button,
  ConfirmAction,
  EmptyState,
  Input,
  Media,
  Select,
  Textarea,
} from "@/components/ui";

import {
  PERSON_ROLE_OPTIONS,
  newStudioPerson,
  type StudioPerson,
} from "./people-utils";
import { StudioItemCard, StudioMicrocopy } from "./studio-ui";

function movePerson(
  list: StudioPerson[],
  from: number,
  to: number,
): StudioPerson[] {
  if (to < 0 || to >= list.length) return list;
  const next = [...list];
  const [row] = next.splice(from, 1);
  next.splice(to, 0, row);
  return next.map((person, index) => ({ ...person, sort_order: index }));
}

export function PeopleLineupBuilder({
  people,
  onChange,
  eventId,
}: {
  people: StudioPerson[];
  onChange: (people: StudioPerson[]) => void;
  eventId?: string;
}) {
  function update(localId: string, patch: Partial<StudioPerson>) {
    onChange(
      people.map((person) =>
        person.localId === localId ? { ...person, ...patch } : person,
      ),
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm font-semibold text-foreground">Lineup</p>
        <StudioMicrocopy>
          Artists, DJs, speakers, comedians, ministers, hosts, and panelists.
          Reorder with Move up / Move down — order is what guests see.
        </StudioMicrocopy>
      </div>

      {people.length === 0 ? (
        <EmptyState
          title="No people yet"
          description="Add the names guests will recognize on the bill."
          action={
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                onChange([newStudioPerson({ role: "Artist", sort_order: 0 })])
              }
            >
              Add person
            </Button>
          }
        />
      ) : null}

      {people.map((person, index) => {
        const roleKnown = PERSON_ROLE_OPTIONS.some(
          (opt) => opt.value === (person.role || ""),
        );
        return (
          <StudioItemCard
            key={person.localId}
            title={`Person ${index + 1}${person.name.trim() ? ` · ${person.name.trim()}` : ""}${person.role ? ` · ${person.role}` : ""}`}
            actions={
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={index === 0}
                  onClick={() => onChange(movePerson(people, index, index - 1))}
                >
                  Move up
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={index >= people.length - 1}
                  onClick={() => onChange(movePerson(people, index, index + 1))}
                >
                  Move down
                </Button>
                <ConfirmAction
                  label="Remove"
                  title="Remove this person from the lineup?"
                  description="They are removed from the public lineup when you save."
                  confirmLabel="Remove"
                  tone="danger"
                  variant="ghost"
                  onConfirm={() =>
                    onChange(
                      people.filter((row) => row.localId !== person.localId),
                    )
                  }
                />
              </>
            }
          >
            <div className="grid gap-3 sm:grid-cols-[96px_minmax(0,1fr)]">
              <div className="relative aspect-square overflow-hidden rounded-[var(--radius-md)] border border-border bg-surface-dark">
                {person.image_url?.trim() ? (
                  <Media
                    src={person.image_url}
                    alt=""
                    className="object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center px-2 text-center text-[10px] font-bold uppercase tracking-wide text-subtle-foreground">
                    Photo
                  </div>
                )}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  label="Name"
                  required
                  hint="Stage or full name guests will recognize."
                  value={person.name}
                  onChange={(e) =>
                    update(person.localId, { name: e.target.value })
                  }
                />
                <div className="space-y-3">
                  <Select
                    label="Role"
                    hint="How they appear on the bill."
                    value={roleKnown ? person.role || "Artist" : "Other"}
                    onChange={(e) => {
                      const next = e.target.value;
                      if (next === "Other") {
                        update(person.localId, {
                          role: roleKnown ? "" : person.role || "",
                        });
                        return;
                      }
                      update(person.localId, { role: next });
                    }}
                  >
                    {PERSON_ROLE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </Select>
                  {!roleKnown || person.role === "Other" || person.role === "" ? (
                    <Input
                      label="Custom role"
                      hint="e.g. Headliner, MC, Worship lead."
                      value={
                        person.role === "Other" ? "" : (person.role ?? "")
                      }
                      onChange={(e) =>
                        update(person.localId, { role: e.target.value })
                      }
                      placeholder="Custom role"
                    />
                  ) : null}
                </div>
              </div>
            </div>

            <Textarea
              label="Bio"
              rows={2}
              hint="Optional short intro — one or two sentences is enough."
              value={person.bio ?? ""}
              onChange={(e) => update(person.localId, { bio: e.target.value })}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <ImageUrlOrUploadField
                label="Photo"
                hint="Portrait or promo photo. Upload from your device or paste a URL."
                value={person.image_url ?? ""}
                onChange={(url) => update(person.localId, { image_url: url })}
                eventId={eventId}
                mediaType="other"
                showPreview={false}
              />
              <Input
                label="Social URL"
                hint="Optional Instagram, X, LinkedIn, or website."
                value={person.social_url ?? ""}
                onChange={(e) =>
                  update(person.localId, { social_url: e.target.value })
                }
                placeholder="https://"
              />
            </div>
            <Input
              label="Performance time"
              type="datetime-local"
              hint="Optional slot when they are on — helps guests plan arrival."
              value={person.performance_time ?? ""}
              onChange={(e) =>
                update(person.localId, { performance_time: e.target.value })
              }
            />
          </StudioItemCard>
        );
      })}

      {people.length > 0 ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() =>
            onChange([
              ...people,
              newStudioPerson({ sort_order: people.length }),
            ])
          }
        >
          Add person
        </Button>
      ) : null}
    </div>
  );
}

export {
  PERSON_ROLE_OPTIONS,
  newStudioPerson,
  toStudioPeople,
  type StudioPerson,
} from "./people-utils";
