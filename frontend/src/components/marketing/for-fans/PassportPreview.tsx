import { Media } from "@/components/ui";
import { brand } from "@/lib/brand";

/** Static Fan Passport mock for marketing — decorative, not live data. */
export function PassportPreview() {
  return (
    <aside
      aria-hidden
      className="relative mx-auto w-full max-w-md overflow-hidden rounded-[var(--radius-xl)] border border-paper/12 bg-card shadow-[var(--shadow-md)] dark:bg-surface-elevated"
    >
      <div className="relative overflow-hidden bg-ink px-5 pb-5 pt-4 text-paper sm:px-6">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.14]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, transparent, transparent 10px, color-mix(in srgb, var(--paper) 14%, transparent) 10px, color-mix(in srgb, var(--paper) 14%, transparent) 11px)",
          }}
        />
        <div className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-primary/25 blur-2xl" />
        <div className="relative flex items-start gap-3.5">
          <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full bg-surface-dark ring-2 ring-primary/55">
            <Media
              src="/demo/fans/miralagos-avatar.svg"
              alt=""
              className="h-full w-full object-cover"
            />
          </div>
          <div className="min-w-0 flex-1 pt-0.5">
            <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-primary">
              Fan Passport
            </p>
            <p className="mt-1 text-lg font-extrabold tracking-tight text-paper">
              Mira Lagos
            </p>
            <p className="text-sm font-semibold text-paper/60">@miralagos</p>
          </div>
        </div>
      </div>

      <div className="space-y-4 p-5 sm:p-6">
        <p className="text-sm leading-relaxed text-body">
          Nightlife history on {brand.name} — badges, verified nights, and
          reviews you control.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {["Lagos", "Afrobeats", "Early bird", "Regular"].map((label) => (
            <span
              key={label}
              className="rounded-md border border-border bg-surface-muted px-2 py-0.5 text-xs font-semibold text-heading dark:bg-surface-inset"
            >
              {label}
            </span>
          ))}
        </div>
        <dl className="grid grid-cols-3 gap-2 rounded-[var(--radius-lg)] border border-border/80 bg-surface-muted/70 px-3 py-3 dark:bg-surface-inset/60">
          {[
            { label: "Nights", value: "24" },
            { label: "Hosts", value: "8" },
            { label: "Connect", value: "12" },
          ].map((stat) => (
            <div key={stat.label}>
              <dt className="text-xs font-semibold text-muted-foreground">
                {stat.label}
              </dt>
              <dd className="mt-0.5 text-xl font-extrabold tabular-nums tracking-tight text-heading">
                {stat.value}
              </dd>
            </div>
          ))}
        </dl>
        <p className="text-xs font-semibold text-muted-foreground">
          Latest stamp · Detty Friday Live
        </p>
      </div>
    </aside>
  );
}
