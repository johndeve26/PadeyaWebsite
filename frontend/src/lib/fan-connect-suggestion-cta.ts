import type { FanConnectSuggestion } from "@/lib/types/fan-connect";

export type FanConnectSuggestionCardCta =
  | "connect"
  | "request_sent"
  | "message"
  | "decline_cooldown";

export function suggestionCtaFromState(
  state: string | undefined,
): FanConnectSuggestionCardCta {
  if (state === "request_pending") return "request_sent";
  if (state === "message") return "message";
  if (state === "decline_cooldown") return "decline_cooldown";
  return "connect";
}

export function suggestionCta(
  s: Pick<FanConnectSuggestion, "cta_state">,
): FanConnectSuggestionCardCta {
  return suggestionCtaFromState(s.cta_state);
}
