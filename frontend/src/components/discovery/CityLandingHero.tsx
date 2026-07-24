import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

export function CityLandingHero({
  title,
  description,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "space-y-4 border-b border-border pb-8 sm:pb-10",
        className,
      )}
    >
      {children ? <div className="min-w-0">{children}</div> : null}
      <div className="max-w-3xl space-y-2.5">
        <h1 className="text-balance text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          {title}
        </h1>
        {description ? (
          <p className="max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
            {description}
          </p>
        ) : null}
      </div>
    </header>
  );
}
