"use client";

type Props = {
  checked: boolean;
  disabled?: boolean;
  label?: string;
  onChange: (next: boolean) => void;
};

export function LegacyVisibilityToggle({
  checked,
  disabled,
  label = "Visible",
  onChange,
}: Props) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-semibold text-foreground">
      <span
        className={[
          "relative h-6 w-11 rounded-full transition-colors",
          checked ? "bg-accent" : "bg-border-strong",
          disabled ? "opacity-50" : "",
        ].join(" ")}
      >
        <input
          type="checkbox"
          className="peer sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span
          className={[
            "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-paper shadow transition-transform",
            checked ? "translate-x-5" : "translate-x-0",
          ].join(" ")}
        />
      </span>
      <span className="text-muted-foreground">{label}</span>
    </label>
  );
}
