import type {
  AssistantSuggestedPrompt,
  AssistantWelcomeRole,
} from "@/lib/types/assistant";

/** Role-aware welcome prompts — keep in sync with docs/AI_ASSISTANT.md. */
const PROMPTS: Record<AssistantWelcomeRole, AssistantSuggestedPrompt[]> = {
  public: [
    {
      id: "public-ibadan",
      label: "Events in Ibadan this weekend",
      message: "Find events in Ibadan this weekend",
    },
    {
      id: "public-free",
      label: "Show me free events",
      message: "Show me free events",
    },
    {
      id: "public-ambassadors",
      label: "How do Pàdéyá Ambassadors work?",
      message: "How do Pàdéyá Ambassadors work?",
    },
    {
      id: "public-host",
      label: "How do I become a host?",
      message: "How do I become a host?",
    },
    {
      id: "public-support",
      label: "Where can I contact support?",
      message: "Where can I contact support?",
    },
  ],
  fan: [
    {
      id: "fan-tickets",
      label: "Show my upcoming tickets",
      message: "Show my upcoming tickets",
    },
    {
      id: "fan-near",
      label: "Find events near me",
      message: "Find events near me",
    },
    {
      id: "fan-passport",
      label: "Where is my Fan Passport?",
      message: "Where is my Fan Passport?",
    },
    {
      id: "fan-saved",
      label: "Show my saved events",
      message: "Show my saved events",
    },
    {
      id: "fan-order",
      label: "Help with an order",
      message: "Help with an order",
    },
  ],
  host: [
    {
      id: "host-events",
      label: "Show my active events",
      message: "Show my active events",
    },
    {
      id: "host-create",
      label: "Where can I create an event?",
      message: "Where can I create an event?",
    },
    {
      id: "host-sales",
      label: "Explain my sales dashboard",
      message: "Explain my sales dashboard",
    },
    {
      id: "host-legacy",
      label: "Show my Legacy progress",
      message: "Show my Legacy progress",
    },
    {
      id: "host-draft",
      label: "Help me draft an event description",
      message: "Help me draft an event description",
    },
  ],
  ambassador: [
    {
      id: "amb-links",
      label: "Show my referral links",
      message: "Show my referral links",
    },
    {
      id: "amb-earnings",
      label: "Explain my earnings",
      message: "Explain my earnings",
    },
    {
      id: "amb-programs",
      label: "Show my active programs",
      message: "Show my active programs",
    },
    {
      id: "amb-payouts",
      label: "Where are my payouts?",
      message: "Where are my payouts?",
    },
    {
      id: "amb-funding",
      label: "Explain host-funded and Pàdéyá-funded commission",
      message: "Explain host-funded and Pàdéyá-funded commission",
    },
  ],
  sponsor: [
    {
      id: "sponsor-ops",
      label: "Show sponsorship opportunities",
      message: "Show sponsorship opportunities",
    },
    {
      id: "sponsor-apps",
      label: "Where are my applications?",
      message: "Where are my applications?",
    },
    {
      id: "sponsor-message",
      label: "Help me prepare a sponsorship message",
      message: "Help me prepare a sponsorship message",
    },
  ],
  admin: [
    {
      id: "admin-liabilities",
      label: "Navigate to referral liabilities",
      message: "Navigate to referral liabilities",
    },
    {
      id: "admin-taxonomy",
      label: "Open taxonomy management",
      message: "Open taxonomy management",
    },
    {
      id: "admin-page",
      label: "Explain the current admin page",
      message: "Explain the current admin page",
    },
    {
      id: "admin-reporting",
      label: "Find a reporting workspace",
      message: "Find a reporting workspace",
    },
  ],
};

export function resolveWelcomeRole(
  role: string | null | undefined,
): AssistantWelcomeRole {
  const key = (role || "public").toLowerCase();
  if (key in PROMPTS) return key as AssistantWelcomeRole;
  return "public";
}

export function getWelcomePrompts(
  role: string | null | undefined,
): AssistantSuggestedPrompt[] {
  return PROMPTS[resolveWelcomeRole(role)];
}
