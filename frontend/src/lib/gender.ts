export type Gender = "male" | "female" | "prefer_not_to_say";

export type GenderVisibility = "public" | "connections_only" | "private";

export type GenderDisplay = {
  gender: Gender | string | null;
  gender_short: string | null;
  gender_label: string | null;
  gender_visible: boolean;
};

export const GENDER_OPTIONS: Gender[] = [
  "male",
  "female",
  "prefer_not_to_say",
];

export const GENDER_VISIBILITY_OPTIONS: GenderVisibility[] = [
  "public",
  "connections_only",
  "private",
];

export const GENDER_LABELS: Record<Gender, string> = {
  male: "Male",
  female: "Female",
  prefer_not_to_say: "Prefer not to say",
};

export const GENDER_SHORT: Partial<Record<Gender, string>> = {
  male: "M",
  female: "F",
};

export const GENDER_VISIBILITY_LABELS: Record<GenderVisibility, string> = {
  public: "Everyone",
  connections_only: "Connections only",
  private: "Only me",
};

/** Product brief privacy copy — include connect-request exception for connections_only. */
export const GENDER_VISIBILITY_HINTS: Record<GenderVisibility, string> = {
  public: "Shown on your profile and directories by default. Anyone can see it.",
  connections_only:
    "Only accepted connections and people involved in a direct connect request can see it.",
  private: "Gender remains private.",
};

export const DEFAULT_GENDER_VISIBILITY: GenderVisibility = "public";

export const GENDER_PROMPT_DISMISS_KEY = "padeya.gender-prompt.dismissed";

export function isGender(value: unknown): value is Gender {
  return (
    value === "male" || value === "female" || value === "prefer_not_to_say"
  );
}

export function isGenderVisibility(value: unknown): value is GenderVisibility {
  return (
    value === "public" ||
    value === "connections_only" ||
    value === "private"
  );
}

/** Compact badge shows only male/female when the backend already authorized visibility. */
export function resolveGenderBadge(
  value: GenderDisplay | "male" | "female" | null | undefined,
): { short: "M" | "F"; label: "Male" | "Female" } | null {
  if (value == null) return null;
  if (value === "male") return { short: "M", label: "Male" };
  if (value === "female") return { short: "F", label: "Female" };

  if (!value.gender_visible) return null;
  if (value.gender === "prefer_not_to_say") return null;
  if (value.gender === "male" || value.gender_short === "M") {
    return { short: "M", label: "Male" };
  }
  if (value.gender === "female" || value.gender_short === "F") {
    return { short: "F", label: "Female" };
  }
  return null;
}
