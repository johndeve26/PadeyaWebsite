import type { EventCheckoutQuestion } from "@/lib/types/events";

export const CHECKOUT_QUESTION_TYPES = [
  { value: "short_text", label: "Short text" },
  { value: "long_text", label: "Long text" },
  { value: "dropdown", label: "Dropdown" },
  { value: "checkbox", label: "Checkbox" },
  { value: "phone", label: "Phone" },
  { value: "email", label: "Email" },
] as const;

export type StudioQuestion = EventCheckoutQuestion & {
  localId: string;
};

export function newStudioQuestion(
  partial?: Partial<StudioQuestion>,
): StudioQuestion {
  return {
    localId: `question-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    label: "",
    type: "short_text",
    required: false,
    options: [],
    help_text: "",
    sort_order: 0,
    ...partial,
  };
}

export function toStudioQuestions(
  questions: EventCheckoutQuestion[],
): StudioQuestion[] {
  return questions
    .filter((question) => (question.status ?? "active") !== "archived")
    .map((question, index) => ({
      localId: question.id || `question-existing-${index}`,
      id: question.id,
      label: question.label ?? "",
      type: question.type || "short_text",
      required: Boolean(question.required),
      options: question.options ?? [],
      help_text: question.help_text ?? "",
      sort_order: question.sort_order ?? index,
      status: question.status ?? "active",
    }));
}
