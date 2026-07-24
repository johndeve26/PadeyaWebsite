"use client";

import {
  Button,
  ConfirmAction,
  EmptyState,
  Input,
  Select,
  Textarea,
} from "@/components/ui";

import {
  CHECKOUT_QUESTION_TYPES,
  newStudioQuestion,
  type StudioQuestion,
} from "./question-utils";
import { StudioItemCard, StudioMicrocopy } from "./studio-ui";

function moveQuestion(
  list: StudioQuestion[],
  from: number,
  to: number,
): StudioQuestion[] {
  if (to < 0 || to >= list.length) return list;
  const next = [...list];
  const [row] = next.splice(from, 1);
  next.splice(to, 0, row);
  return next.map((question, index) => ({ ...question, sort_order: index }));
}

export function AttendeeQuestionBuilder({
  questions,
  onChange,
}: {
  questions: StudioQuestion[];
  onChange: (questions: StudioQuestion[]) => void;
}) {
  function update(localId: string, patch: Partial<StudioQuestion>) {
    onChange(
      questions.map((question) =>
        question.localId === localId ? { ...question, ...patch } : question,
      ),
    );
  }

  return (
    <div className="space-y-4">
      <StudioMicrocopy>
        Optional questions asked at checkout (WhatsApp number, dietary needs, table
        preference). Removing a question that already has buyer answers archives it
        instead of deleting history. Reorder with Move up / Move down.
      </StudioMicrocopy>
      {questions.length === 0 ? (
        <EmptyState
          title="No checkout questions"
          description="Ask for WhatsApp numbers, dietary notes, or table preferences."
          action={
            <Button
              type="button"
              variant="secondary"
              onClick={() => onChange([newStudioQuestion({ sort_order: 0 })])}
            >
              Add question
            </Button>
          }
        />
      ) : null}
      {questions.map((question, index) => {
        const needsOptions =
          question.type === "dropdown" || question.type === "checkbox";
        return (
          <StudioItemCard
            key={question.localId}
            title={`Question ${index + 1}${question.label.trim() ? ` · ${question.label.trim()}` : ""}`}
            actions={
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={index === 0}
                  onClick={() =>
                    onChange(moveQuestion(questions, index, index - 1))
                  }
                >
                  Move up
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={index >= questions.length - 1}
                  onClick={() =>
                    onChange(moveQuestion(questions, index, index + 1))
                  }
                >
                  Move down
                </Button>
                <ConfirmAction
                  label="Remove"
                  title="Remove this checkout question?"
                  description={
                    question.id
                      ? "If buyers already answered it, the question is archived (answers stay on orders). Otherwise it is deleted when you save."
                      : "Removes this draft question from the Studio list before save."
                  }
                  confirmLabel="Remove"
                  tone="danger"
                  variant="ghost"
                  onConfirm={() =>
                    onChange(
                      questions.filter((row) => row.localId !== question.localId),
                    )
                  }
                />
              </>
            }
          >
            <Input
              label="Label"
              hint="The question text buyers see (e.g. “WhatsApp number for updates”)."
              value={question.label}
              onChange={(e) => update(question.localId, { label: e.target.value })}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Select
                label="Type"
                hint="Short text for names/numbers, long text for notes, dropdown/checkbox for fixed choices."
                value={question.type}
                onChange={(e) =>
                  update(question.localId, { type: e.target.value })
                }
              >
                {CHECKOUT_QUESTION_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </Select>
              <label className="flex flex-col justify-end gap-1 pb-2 text-sm text-foreground">
                <span className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={Boolean(question.required)}
                    onChange={(e) =>
                      update(question.localId, { required: e.target.checked })
                    }
                  />
                  Required
                </span>
                <span className="text-xs text-muted-foreground">
                  Required means the buyer must answer before they can pay.
                </span>
              </label>
            </div>
            <Input
              label="Help text"
              hint="Optional hint under the question (e.g. “Include country code”)."
              value={question.help_text ?? ""}
              onChange={(e) =>
                update(question.localId, { help_text: e.target.value })
              }
            />
            {needsOptions ? (
              <Textarea
                label="Options"
                hint="One choice per line (or comma-separated)."
                value={(question.options ?? []).join("\n")}
                onChange={(e) =>
                  update(question.localId, {
                    options: e.target.value
                      .split(/[\n,]/)
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
              />
            ) : null}
          </StudioItemCard>
        );
      })}
      {questions.length > 0 ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() =>
            onChange([
              ...questions,
              newStudioQuestion({ sort_order: questions.length }),
            ])
          }
        >
          Add question
        </Button>
      ) : null}
    </div>
  );
}
