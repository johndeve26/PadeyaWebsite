"use client";

import { Select } from "@/components/ui";

import type { EventStudioValues } from "./types";

export const EVENT_TYPE_OPTIONS = [
  "public",
  "private",
  "invite_only",
  "secret_location",
  "online",
  "hybrid",
] as const;

export const VISIBILITY_OPTIONS = [
  "listed",
  "unlisted",
  "password_protected",
  "approval_required",
] as const;

function visibilityHelp(visibility: string): string {
  switch (visibility) {
    case "listed":
      return "Appears in Pàdéyá browse, hubs, and search. Best for open public nights.";
    case "unlisted":
      return "Hidden from browse — only people with the link can open the page.";
    case "password_protected":
      return "Guests need a password to view or buy. Password entry UI ships in a later release; set this when you are ready to gate access.";
    case "approval_required":
      return "Guests may request access; you approve before they can complete purchase.";
    default:
      return "Controls how discoverable this event is on Pàdéyá.";
  }
}

function eventTypeHelp(eventType: string): string {
  switch (eventType) {
    case "public":
      return "Open to ticket buyers who meet your ticket rules.";
    case "private":
      return "Closed gathering — keep visibility unlisted or approval-gated.";
    case "invite_only":
      return "Meant for invited guests; pair with unlisted or approval_required.";
    case "secret_location":
      return "Address stays hidden by default — configure reveal rules on Location & Privacy.";
    case "online":
      return "Fully virtual. Set the meeting URL under Location & Privacy.";
    case "hybrid":
      return "In-person plus online. Share both venue privacy and online URL rules.";
    default:
      return "How the night is structured for guests.";
  }
}

/**
 * Event-level access: type + visibility (existing enums; no password field yet).
 */
export function AccessRulesFields({
  values,
  onChange,
}: {
  values: Pick<EventStudioValues, "event_type" | "visibility">;
  onChange: (key: "event_type" | "visibility", value: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Event type"
          hint={eventTypeHelp(values.event_type)}
          value={values.event_type}
          onChange={(e) => onChange("event_type", e.target.value)}
        >
          {EVENT_TYPE_OPTIONS.map((type) => (
            <option key={type} value={type}>
              {type.replaceAll("_", " ")}
            </option>
          ))}
        </Select>
        <Select
          label="Visibility"
          hint={visibilityHelp(values.visibility)}
          value={values.visibility}
          onChange={(e) => onChange("visibility", e.target.value)}
        >
          {VISIBILITY_OPTIONS.map((item) => (
            <option key={item} value={item}>
              {item.replaceAll("_", " ")}
            </option>
          ))}
        </Select>
      </div>
      {values.visibility === "listed" ? (
        <p className="rounded-[var(--radius-md)] border border-border bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
          Listed events need a primary category before submit so hubs and related
          rails stay accurate.
        </p>
      ) : null}
    </div>
  );
}
