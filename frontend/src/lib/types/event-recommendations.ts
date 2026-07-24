import type { EventItem } from "@/lib/types/events";

export type EventRecommendationReason = {
  code: string;
  label: string;
};

export type EventRecommendationFlags = {
  from_followed_host?: boolean;
  similar_to_attended?: boolean;
  near_you?: boolean;
  connected_fans_signal?: boolean;
  category_match?: boolean;
};

export type EventRecommendation = {
  event: EventItem;
  score: number;
  reasons: EventRecommendationReason[];
  flags?: EventRecommendationFlags;
};

export type EventRecommendationsResponse = {
  events: EventRecommendation[];
  next_cursor?: string | null;
  mode: string;
  generated_at: string;
  empty_title?: string | null;
  empty_description?: string | null;
};

export type EventRecommendationImpressionInput = {
  event_id: string;
  surface: string;
  position?: number;
  recommendation_score?: number;
  reason_codes?: string[];
};
