"use client";

import { Badge, Button, Card, Input } from "@/components/ui";

/** Shared admin form shell for taxonomy terms. */
export function TaxonomyForm({
  name,
  slug,
  description,
  seoTitle,
  seoDescription,
  onName,
  onSlug,
  onDescription,
  onSeoTitle,
  onSeoDescription,
  onSubmit,
  submitLabel = "Save",
  busy,
}: {
  name: string;
  slug: string;
  description: string;
  seoTitle: string;
  seoDescription: string;
  onName: (v: string) => void;
  onSlug: (v: string) => void;
  onDescription: (v: string) => void;
  onSeoTitle: (v: string) => void;
  onSeoDescription: (v: string) => void;
  onSubmit: () => void;
  submitLabel?: string;
  busy?: boolean;
}) {
  return (
    <Card className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label="Name" value={name} onChange={(e) => onName(e.target.value)} />
        <Input label="Slug" value={slug} onChange={(e) => onSlug(e.target.value)} />
      </div>
      <Input
        label="Description"
        value={description}
        onChange={(e) => onDescription(e.target.value)}
      />
      <details className="rounded-[var(--radius-md)] border border-border p-3">
        <summary className="cursor-pointer text-sm font-bold text-foreground">
          Search listing (SEO)
        </summary>
        <div className="mt-3 grid gap-3">
          <Input
            label="SEO title"
            value={seoTitle}
            onChange={(e) => onSeoTitle(e.target.value)}
          />
          <Input
            label="SEO description"
            value={seoDescription}
            onChange={(e) => onSeoDescription(e.target.value)}
          />
        </div>
      </details>
      <Button disabled={busy || !name.trim()} onClick={onSubmit}>
        {submitLabel}
      </Button>
    </Card>
  );
}

export function UsageCountBadge({ count }: { count: number }) {
  return (
    <Badge tone={count > 0 ? "warning" : "neutral"} size="sm">
      {count} used
    </Badge>
  );
}

export function TaxonomyManager({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="space-y-4">{children}</div>;
}
