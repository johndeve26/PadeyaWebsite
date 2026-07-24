"use client";

import Link from "next/link";

import { Button, Card } from "@/components/ui";

export type PendingTask = {
  id: string;
  label: string;
  description: string;
  href: string;
  count?: number;
};

export function PendingTasksSection({ tasks }: { tasks: PendingTask[] }) {
  if (tasks.length === 0) return null;

  return (
    <section className="space-y-3">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Needs attention
        </p>
        <h3 className="text-lg font-bold text-foreground">Pending tasks</h3>
      </div>
      <div className="space-y-2">
        {tasks.map((task) => (
          <Card
            key={task.id}
            className="flex flex-wrap items-center justify-between gap-3 py-3"
          >
            <div className="min-w-0">
              <p className="font-bold text-foreground">
                {task.label}
                {task.count != null && task.count > 0 ? (
                  <span className="ml-2 text-sm font-extrabold text-accent">
                    {task.count}
                  </span>
                ) : null}
              </p>
              <p className="text-sm text-muted-foreground">{task.description}</p>
            </div>
            <Link href={task.href}>
              <Button size="sm" variant="secondary">
                Review
              </Button>
            </Link>
          </Card>
        ))}
      </div>
    </section>
  );
}
