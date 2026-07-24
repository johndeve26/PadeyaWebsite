"use client";

import { Input, Select, Textarea } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { EventCheckoutQuestion } from "@/lib/types/events";

export type CheckoutAnswerMap = Record<string, string | string[]>;
export type CheckoutAnswerErrors = Record<string, string>;

function sortedQuestions(questions: EventCheckoutQuestion[]) {
  return [...questions].sort(
    (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
  );
}

function isEmpty(value: string | string[] | undefined): boolean {
  if (Array.isArray(value)) return value.length === 0;
  return !String(value ?? "").trim();
}

function normalizeString(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value.map((v) => String(v).trim()).filter(Boolean).join(", ");
  }
  return String(value ?? "").trim();
}

function validateAnswerFormat(
  question: EventCheckoutQuestion,
  value: string | string[] | undefined,
): string | null {
  if (isEmpty(value)) return null;
  const options = question.options ?? [];
  const raw = normalizeString(value);

  if (question.type === "dropdown") {
    if (options.length && !options.includes(raw)) {
      return "Pick one of the listed options.";
    }
    return null;
  }

  if (question.type === "checkbox") {
    const selected = Array.isArray(value)
      ? value.map((v) => String(v).trim()).filter(Boolean)
      : raw.split(",").map((s) => s.trim()).filter(Boolean);
    if (options.length && selected.some((s) => !options.includes(s))) {
      return "Pick from the listed options.";
    }
    return null;
  }

  if (question.type === "email") {
    const at = raw.indexOf("@");
    const domain = at >= 0 ? raw.slice(at + 1) : "";
    if (at < 1 || !domain.includes(".")) {
      return "Enter a valid email address.";
    }
    return null;
  }

  if (question.type === "phone") {
    const digits = raw.replace(/[^\d+]/g, "");
    if (digits.length < 7) {
      return "Enter a valid phone number.";
    }
    return null;
  }

  return null;
}

/** Field-level + summary validation. Empty questions → no errors. */
export function validateCheckoutAnswers(
  questions: EventCheckoutQuestion[],
  answers: CheckoutAnswerMap,
): { errors: CheckoutAnswerErrors; summary: string | null } {
  const errors: CheckoutAnswerErrors = {};
  for (const question of sortedQuestions(questions)) {
    if (!question.id) continue;
    if (question.required && isEmpty(answers[question.id])) {
      errors[question.id] = "This answer is required.";
      continue;
    }
    const formatError = validateAnswerFormat(question, answers[question.id]);
    if (formatError) errors[question.id] = formatError;
  }
  const first = sortedQuestions(questions).find((q) => q.id && errors[q.id]);
  const summary = first?.id
    ? `Please answer: ${first.label}`
    : null;
  return { errors, summary };
}

export function missingRequiredAnswers(
  questions: EventCheckoutQuestion[],
  answers: CheckoutAnswerMap,
): string | null {
  return validateCheckoutAnswers(questions, answers).summary;
}

export function answersToPayload(answers: CheckoutAnswerMap) {
  return Object.entries(answers)
    .map(([question_id, value]) => ({
      question_id,
      value,
    }))
    .filter((row) => {
      if (Array.isArray(row.value)) return row.value.length > 0;
      return String(row.value ?? "").trim().length > 0;
    });
}

export function CheckoutQuestionsFields({
  questions,
  answers,
  onChange,
  errors = {},
}: {
  questions: EventCheckoutQuestion[];
  answers: CheckoutAnswerMap;
  onChange: (answers: CheckoutAnswerMap) => void;
  errors?: CheckoutAnswerErrors;
}) {
  const ordered = sortedQuestions(questions).filter((q) => Boolean(q.id));
  if (ordered.length === 0) return null;

  function setValue(questionId: string, value: string | string[]) {
    onChange({ ...answers, [questionId]: value });
  }

  function toggleCheckbox(questionId: string, option: string, checked: boolean) {
    const current = answers[questionId];
    const selected = Array.isArray(current)
      ? [...current]
      : typeof current === "string" && current
        ? current.split(",").map((s) => s.trim()).filter(Boolean)
        : [];
    const next = checked
      ? selected.includes(option)
        ? selected
        : [...selected, option]
      : selected.filter((item) => item !== option);
    setValue(questionId, next);
  }

  return (
    <div id="checkout-questions" className="space-y-4">
      <div>
        <h3 className="text-lg font-extrabold tracking-tight text-foreground">
          A few questions
        </h3>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
          The host asked for this with your order. Required fields are marked
          with *. Answers are saved with your order — tickets still only issue
          after payment confirmation.
        </p>
      </div>
      {ordered.map((question) => {
        const id = question.id as string;
        const label = question.required
          ? `${question.label} *`
          : question.label;
        const hint = question.help_text || undefined;
        const error = errors[id];
        const value = answers[id] ?? (question.type === "checkbox" ? [] : "");

        if (question.type === "long_text") {
          return (
            <Textarea
              key={id}
              label={label}
              hint={hint}
              error={error}
              value={typeof value === "string" ? value : ""}
              onChange={(e) => setValue(id, e.target.value)}
              required={Boolean(question.required)}
            />
          );
        }

        if (question.type === "dropdown") {
          return (
            <Select
              key={id}
              label={label}
              hint={hint}
              error={error}
              value={typeof value === "string" ? value : ""}
              onChange={(e) => setValue(id, e.target.value)}
              required={Boolean(question.required)}
            >
              <option value="">Select…</option>
              {(question.options ?? []).map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          );
        }

        if (question.type === "checkbox") {
          const selected = Array.isArray(value)
            ? value
            : typeof value === "string" && value
              ? value.split(",").map((s) => s.trim()).filter(Boolean)
              : [];
          return (
            <fieldset
              key={id}
              className={cn(
                "space-y-2 rounded-[var(--radius-md)] border px-3 py-3",
                error ? "border-danger" : "border-border",
              )}
            >
              <legend className="px-1 text-sm font-semibold text-foreground">
                {label}
              </legend>
              {hint ? (
                <p className="text-xs text-muted-foreground">{hint}</p>
              ) : null}
              <div className="space-y-2">
                {(question.options ?? []).map((option) => (
                  <label
                    key={option}
                    className="flex items-center gap-2 text-sm text-foreground"
                  >
                    <input
                      type="checkbox"
                      checked={selected.includes(option)}
                      onChange={(e) =>
                        toggleCheckbox(id, option, e.target.checked)
                      }
                    />
                    {option}
                  </label>
                ))}
              </div>
              {error ? (
                <p className="text-xs font-medium text-danger">{error}</p>
              ) : null}
            </fieldset>
          );
        }

        const inputType =
          question.type === "email"
            ? "email"
            : question.type === "phone"
              ? "tel"
              : "text";

        return (
          <Input
            key={id}
            label={label}
            hint={hint}
            error={error}
            type={inputType}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => setValue(id, e.target.value)}
            required={Boolean(question.required)}
            autoComplete={
              question.type === "email"
                ? "email"
                : question.type === "phone"
                  ? "tel"
                  : "on"
            }
          />
        );
      })}
    </div>
  );
}
