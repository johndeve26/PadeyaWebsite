/** Admin internal note types — keep in sync with backend `app.users.note_constants`. */

export const USER_NOTE_TYPES = [
  "general",
  "support",
  "fraud",
  "moderation",
  "finance",
  "security",
] as const;

export type UserNoteType = (typeof USER_NOTE_TYPES)[number];

export const USER_NOTE_TYPE_LABELS: Record<UserNoteType, string> = {
  general: "General",
  support: "Support",
  fraud: "Fraud",
  moderation: "Moderation",
  finance: "Finance",
  security: "Security",
};
