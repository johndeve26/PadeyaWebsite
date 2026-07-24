/**
 * Typing indicator copy. Prefer a safe display name; never contact fields.
 * fan_fan threads should pass display_name only (not username / email / phone).
 */
export function formatTypingLabel(displayName?: string | null): string {
  const name = (displayName || "").trim();
  if (!name) return "Typing…";
  return `${name} is typing…`;
}
