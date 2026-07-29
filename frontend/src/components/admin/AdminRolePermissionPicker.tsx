"use client";

import { useMemo, useState } from "react";

import { Button, Input } from "@/components/ui";
import type { AdminPermissionGroup } from "@/lib/admin-team/api";

type Props = {
  catalog: AdminPermissionGroup[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
  /** When true, checkboxes are visible but not editable (system role view). */
  readOnly?: boolean;
};

export function AdminRolePermissionPicker({
  catalog,
  selected,
  onChange,
  readOnly = false,
}: Props) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return catalog;
    return catalog
      .map((group) => ({
        ...group,
        permissions: group.permissions.filter(
          (p) =>
            p.code.toLowerCase().includes(q) ||
            p.description.toLowerCase().includes(q) ||
            group.group.toLowerCase().includes(q),
        ),
      }))
      .filter((g) => g.permissions.length > 0);
  }, [catalog, query]);

  const selectedCount = selected.size;

  function toggle(code: string) {
    if (readOnly) return;
    const next = new Set(selected);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    onChange(next);
  }

  function setGroup(codes: string[], enabled: boolean) {
    if (readOnly) return;
    const next = new Set(selected);
    for (const code of codes) {
      if (enabled) next.add(code);
      else next.delete(code);
    }
    onChange(next);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <Input
          label="Search features"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. refund, blog, users"
          className="max-w-sm"
        />
        <p className="text-sm text-muted-foreground">
          {selectedCount} feature{selectedCount === 1 ? "" : "s"} selected
          {readOnly ? " · read-only" : ""}
        </p>
      </div>

      <p className="text-sm text-muted-foreground">
        Tick individual features. Groups are only for organization — use Select
        all / Clear as shortcuts, then fine-tune each checkbox.
      </p>

      {filtered.map((group) => {
        const codes = group.permissions.map((p) => p.code);
        const onCount = codes.filter((c) => selected.has(c)).length;
        const allOn = onCount === codes.length && codes.length > 0;
        return (
          <fieldset
            key={group.group}
            className="space-y-3 rounded-[var(--radius-md)] border border-border p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <legend className="font-semibold text-heading">
                {group.group}
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {onCount}/{codes.length}
                </span>
              </legend>
              {!readOnly ? (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={allOn}
                    onClick={() => setGroup(codes, true)}
                  >
                    Select all
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={onCount === 0}
                    onClick={() => setGroup(codes, false)}
                  >
                    Clear
                  </Button>
                </div>
              ) : null}
            </div>
            <ul className="space-y-2">
              {group.permissions.map((perm) => (
                <li key={perm.code}>
                  <label className="flex cursor-pointer items-start gap-3 text-sm">
                    <input
                      type="checkbox"
                      className="mt-1 accent-[var(--brand-green)]"
                      checked={selected.has(perm.code)}
                      disabled={readOnly}
                      onChange={() => toggle(perm.code)}
                    />
                    <span>
                      <span className="font-medium text-heading">
                        {perm.description || perm.code}
                      </span>
                      {perm.high_level ? (
                        <span className="ml-2 text-xs text-muted-foreground">
                          (super admin only)
                        </span>
                      ) : null}
                      <span className="block font-mono text-xs text-muted-foreground">
                        {perm.code}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
        );
      })}

      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No features match that search.</p>
      ) : null}
    </div>
  );
}
