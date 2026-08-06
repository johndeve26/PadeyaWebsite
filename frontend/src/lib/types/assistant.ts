/** Types for Ask Pàdéyá / Pàdéyá Copilot. */

export type AssistantMode = "public" | "authenticated";

export type AssistantStatus = {
  assistant_enabled: boolean;
  public_enabled: boolean;
  authenticated_enabled: boolean;
  actions_enabled: boolean;
  event_search_enabled: boolean;
  product_public: string;
  product_authenticated: string;
};

export type AssistantPageContext = {
  route_key?: string | null;
  page_title?: string | null;
  role?: string | null;
  entity_public_id?: string | null;
  active_tab?: string | null;
  ui_errors?: string[];
  feature_flags?: Record<string, boolean>;
  available_actions?: string[];
};

export type AssistantCitation = {
  title: string;
  url: string;
  snippet?: string | null;
  source_type?: string | null;
  route_key?: string | null;
};

export type AssistantCardType =
  | "event"
  | "host"
  | "route"
  | "confirmation"
  | "support"
  | string;

export type AssistantCard = {
  type: AssistantCardType;
  title: string;
  subtitle?: string | null;
  url?: string | null;
  image_url?: string | null;
  meta?: Record<string, unknown>;
};

export type AssistantAction = {
  type: string;
  label: string;
  route_key?: string | null;
  url?: string | null;
  tool_name?: string | null;
  confirmation_id?: string | null;
  requires_confirmation?: boolean;
  meta?: Record<string, unknown>;
};

export type AssistantChatRequest = {
  message: string;
  session_id?: string | null;
  page_context?: AssistantPageContext | null;
  timezone?: string | null;
};

export type AssistantFeedbackRating =
  | "up"
  | "down"
  | "helpful"
  | "not_helpful";

export type AssistantFeedbackCreate = {
  session_id: string;
  message_id: string;
  rating: AssistantFeedbackRating;
  reason?: string | null;
  comment?: string | null;
};

export type AssistantSession = {
  id: string;
  mode: string;
  title?: string | null;
  active_role?: string | null;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type AssistantMessageRole = "user" | "assistant" | "system" | "tool";

export type AssistantMessagePublic = {
  id: string;
  role: AssistantMessageRole | string;
  content: string;
  structured_content_json?: Record<string, unknown> | null;
  safety_status?: string | null;
  created_at: string;
};

export type AssistantSessionDetail = AssistantSession & {
  messages: AssistantMessagePublic[];
};

/** Client-side chat message (streaming + history). */
export type AssistantChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  streaming?: boolean;
  error?: boolean;
  messageId?: string | null;
  citations?: AssistantCitation[];
  cards?: AssistantCard[];
  actions?: AssistantAction[];
  confirmationId?: string | null;
  safetyStatus?: string | null;
  usedFallback?: boolean;
};

export type AssistantSseEventType =
  | "status"
  | "session"
  | "token"
  | "card"
  | "action"
  | "tool"
  | "citation"
  | "error"
  | "done"
  | string;

export type AssistantSseEvent = {
  event: AssistantSseEventType;
  data: Record<string, unknown>;
};

export type AssistantDonePayload = {
  ok?: boolean;
  session_id?: string;
  message_id?: string | null;
  mode?: string;
  product_name?: string;
  text?: string;
  citations?: AssistantCitation[];
  cards?: AssistantCard[];
  actions?: AssistantAction[];
  safety_status?: string | null;
  used_fallback?: boolean;
  provider?: string | null;
  model?: string | null;
  intent?: string | null;
  confirmation_id?: string | null;
  trace_id?: string | null;
};

export type AssistantWelcomeRole =
  | "public"
  | "fan"
  | "host"
  | "ambassador"
  | "sponsor"
  | "admin";

export type AssistantSuggestedPrompt = {
  id: string;
  label: string;
  message: string;
};
