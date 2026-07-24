"use client";

import { type FormEvent, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";
import { fieldControlClass } from "@/lib/ui/field";

import { Button } from "./Button";

export type SearchBarProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "onSubmit" | "type"
> & {
  onSubmitSearch?: (value: string) => void;
  submitLabel?: string;
  className?: string;
};

export function SearchBar({
  onSubmitSearch,
  submitLabel = "Search",
  className = "",
  defaultValue,
  value,
  onChange,
  placeholder = "Search…",
  ...props
}: SearchBarProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onSubmitSearch) return;
    const data = new FormData(event.currentTarget);
    onSubmitSearch(String(data.get("q") ?? ""));
  }

  return (
    <form
      className={cn("flex w-full flex-col gap-2 sm:flex-row sm:items-center", className)}
      onSubmit={handleSubmit}
      role="search"
    >
      <input
        name="q"
        type="search"
        placeholder={placeholder}
        defaultValue={defaultValue}
        value={value}
        onChange={onChange}
        className={fieldControlClass({
          className: "h-11 flex-1 px-3.5",
        })}
        {...props}
      />
      {onSubmitSearch ? (
        <Button type="submit" variant="secondary" className="sm:w-auto">
          {submitLabel}
        </Button>
      ) : null}
    </form>
  );
}
