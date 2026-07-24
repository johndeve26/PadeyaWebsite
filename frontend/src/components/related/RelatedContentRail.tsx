import Link from "next/link";
import { Children, type ReactNode } from "react";

import { cn } from "@/lib/cn";

export function RelatedContentRail({
  title,
  seeAllHref,
  children,
  className = "",
}: {
  title: string;
  seeAllHref?: string;
  children: ReactNode;
  className?: string;
}) {
  if (Children.count(children) === 0) return null;

  return (
    <section className={cn("space-y-4", className)}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
          {title}
        </h2>
        {seeAllHref ? (
          <Link
            href={seeAllHref}
            className="text-sm font-semibold text-foreground underline-offset-4 hover:underline"
          >
            See all
          </Link>
        ) : null}
      </div>
      <div className="-mx-1 overflow-x-auto">
        <div className="flex w-max gap-3 px-1 pb-1 sm:gap-4">{children}</div>
      </div>
    </section>
  );
}
