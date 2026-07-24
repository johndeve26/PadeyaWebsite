import type { EventPerson } from "@/lib/types/events";

import { toLocalInput } from "./agenda-utils";

/** Suggested roles for Event Studio lineup use cases. */
export const PERSON_ROLE_OPTIONS = [
  { value: "Artist", label: "Artist" },
  { value: "DJ", label: "DJ" },
  { value: "Speaker", label: "Speaker" },
  { value: "Comedian", label: "Comedian" },
  { value: "Minister", label: "Minister" },
  { value: "Host", label: "Host" },
  { value: "Panelist", label: "Panelist" },
  { value: "Performer", label: "Performer" },
  { value: "Other", label: "Other" },
] as const;

export type StudioPerson = EventPerson & {
  localId: string;
};

export function newStudioPerson(
  partial?: Partial<StudioPerson>,
): StudioPerson {
  return {
    localId: `person-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    name: "",
    role: "Artist",
    bio: "",
    image_url: "",
    social_url: "",
    performance_time: "",
    sort_order: 0,
    ...partial,
  };
}

export function toStudioPeople(people: EventPerson[]): StudioPerson[] {
  return people.map((person, index) => ({
    localId: person.id || `person-existing-${index}`,
    id: person.id,
    name: person.name ?? "",
    role: person.role ?? "Artist",
    bio: person.bio ?? "",
    image_url: person.image_url ?? "",
    social_url: person.social_url ?? "",
    performance_time: toLocalInput(person.performance_time),
    sort_order: person.sort_order ?? index,
  }));
}
