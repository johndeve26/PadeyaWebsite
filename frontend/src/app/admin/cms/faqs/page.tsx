"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  archiveFaq,
  createFaq,
  fetchAdminFaqs,
  publishFaq,
  restoreFaq,
  updateFaq,
} from "@/lib/cms-api";
import type { CmsFaq } from "@/lib/types/lifecycle";

type CreateForm = {
  question: string;
  answer: string;
  category: string;
  sort_order: string;
};

const emptyCreate: CreateForm = {
  question: "",
  answer: "",
  category: "general",
  sort_order: "0",
};

export default function AdminFaqsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<CmsFaq[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(true);
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate);
  const [createBusy, setCreateBusy] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editQuestion, setEditQuestion] = useState("");
  const [editAnswer, setEditAnswer] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editSortOrder, setEditSortOrder] = useState("0");
  const [editBusy, setEditBusy] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchAdminFaqs(includeArchived);
    setRows(data);
  }, [includeArchived]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load FAQs");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  function selectRow(faq: CmsFaq) {
    setSelectedId(faq.id);
    setEditQuestion(faq.question);
    setEditAnswer(faq.answer);
    setEditCategory(faq.category);
    setEditSortOrder(String(faq.sort_order));
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!createForm.question.trim() || !createForm.answer.trim()) return;
    setCreateBusy(true);
    try {
      await createFaq({
        question: createForm.question.trim(),
        answer: createForm.answer.trim(),
        category: createForm.category.trim() || "general",
        sort_order: Number(createForm.sort_order) || 0,
      });
      setCreateForm(emptyCreate);
      toast.push({ tone: "success", title: "FAQ created" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Create failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setCreateBusy(false);
    }
  }

  async function onSaveEdit() {
    if (!selectedId || !editQuestion.trim() || !editAnswer.trim()) return;
    setEditBusy(true);
    try {
      await updateFaq(selectedId, {
        question: editQuestion.trim(),
        answer: editAnswer.trim(),
        category: editCategory.trim() || "general",
        sort_order: Number(editSortOrder) || 0,
      });
      toast.push({ tone: "success", title: "FAQ updated" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Update failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setEditBusy(false);
    }
  }

  async function runLifecycle(
    id: string,
    action: "publish" | "archive" | "restore",
  ) {
    setBusyId(id);
    try {
      if (action === "publish") await publishFaq(id);
      else if (action === "archive") await archiveFaq(id);
      else await restoreFaq(id);
      toast.push({
        tone: "success",
        title:
          action === "publish"
            ? "FAQ published"
            : action === "archive"
              ? "FAQ archived"
              : "FAQ restored",
      });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Action failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  function lifecycleActions(faq: CmsFaq) {
    const busy = busyId === faq.id;
    if (faq.status === "draft") {
      return (
        <ConfirmAction
          label="Publish"
          title="Publish this FAQ?"
          description="It will appear on the public help centre."
          confirmLabel="Publish"
          busy={busy}
          onConfirm={() => runLifecycle(faq.id, "publish")}
        />
      );
    }
    if (faq.status === "published") {
      return (
        <ConfirmAction
          label="Archive"
          title="Archive this FAQ?"
          description="Removes it from the public help centre."
          confirmLabel="Archive"
          tone="danger"
          busy={busy}
          onConfirm={() => runLifecycle(faq.id, "archive")}
        />
      );
    }
    if (faq.status === "archived") {
      return (
        <ConfirmAction
          label="Restore"
          title="Restore this FAQ?"
          description="Returns to draft for editing."
          confirmLabel="Restore"
          busy={busy}
          onConfirm={() => runLifecycle(faq.id, "restore")}
        />
      );
    }
    return null;
  }

  const selected = rows?.find((f) => f.id === selectedId) ?? null;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="CMS"
      title="FAQs"
      description="Help centre questions — publish and archive instead of delete."
    >
      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {rows ? (
        <div className="space-y-8">
          <Card className="space-y-4">
            <SectionHeader eyebrow="New" title="Create FAQ" />
            <form onSubmit={(e) => void onCreate(e)} className="space-y-4">
              <Input
                label="Question"
                value={createForm.question}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, question: e.target.value }))
                }
                required
              />
              <Textarea
                label="Answer"
                value={createForm.answer}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, answer: e.target.value }))
                }
                rows={4}
                required
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Category"
                  value={createForm.category}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, category: e.target.value }))
                  }
                />
                <Input
                  label="Sort order"
                  type="number"
                  value={createForm.sort_order}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, sort_order: e.target.value }))
                  }
                />
              </div>
              <Button
                type="submit"
                disabled={
                  createBusy ||
                  !createForm.question.trim() ||
                  !createForm.answer.trim()
                }
              >
                {createBusy ? "Creating…" : "Create FAQ"}
              </Button>
            </form>
          </Card>

          <FilterBar>
            <label className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border accent-primary"
                checked={includeArchived}
                onChange={(e) => setIncludeArchived(e.target.checked)}
              />
              Include archived
            </label>
          </FilterBar>

          {rows.length === 0 && !error ? (
            <EmptyState title="No FAQs yet" description="Create your first FAQ above." />
          ) : (
            <DataTable
              rows={rows}
              rowKey={(f) => f.id}
              emptyTitle="No FAQs"
              columns={[
                {
                  key: "question",
                  header: "Question",
                  primary: true,
                  cell: (f) => (
                    <button
                      type="button"
                      className="text-left font-semibold text-foreground underline-offset-2 hover:underline"
                      onClick={() => selectRow(f)}
                    >
                      {f.question}
                    </button>
                  ),
                },
                {
                  key: "category",
                  header: "Category",
                  cell: (f) => f.category,
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (f) => <StatusBadge status={f.status} />,
                },
                {
                  key: "order",
                  header: "Order",
                  cell: (f) => f.sort_order,
                },
                {
                  key: "actions",
                  header: "",
                  cell: (f) => (
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="ghost" onClick={() => selectRow(f)}>
                        Edit
                      </Button>
                      {lifecycleActions(f)}
                    </div>
                  ),
                },
              ]}
            />
          )}

          {selected ? (
            <Card className="space-y-4 border-accent/30">
              <SectionHeader eyebrow="Edit" title="Selected FAQ" />
              <Input
                label="Question"
                value={editQuestion}
                onChange={(e) => setEditQuestion(e.target.value)}
              />
              <Textarea
                label="Answer"
                value={editAnswer}
                onChange={(e) => setEditAnswer(e.target.value)}
                rows={5}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Category"
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                />
                <Input
                  label="Sort order"
                  type="number"
                  value={editSortOrder}
                  onChange={(e) => setEditSortOrder(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={
                    editBusy || !editQuestion.trim() || !editAnswer.trim()
                  }
                  onClick={() => void onSaveEdit()}
                >
                  {editBusy ? "Saving…" : "Save changes"}
                </Button>
                <Button variant="ghost" onClick={() => setSelectedId(null)}>
                  Close
                </Button>
                {lifecycleActions(selected)}
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      {rows == null && !error ? <SkeletonLoader lines={4} /> : null}
    </DashboardShell>
  );
}
