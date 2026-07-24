"use client";

import { Select } from "@/components/ui";
import { cn } from "@/lib/cn";

export type SortOption = {
  value: string;
  label: string;
};

export function SortSelect({
  value,
  onChange,
  options,
  label = "Sort by",
  className = "",
}: {
  value: string;
  onChange: (value: string) => void;
  options: SortOption[];
  label?: string;
  className?: string;
}) {
  return (
    <Select
      label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(className)}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </Select>
  );
}
