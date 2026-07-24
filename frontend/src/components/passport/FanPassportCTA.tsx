"use client";

import Link from "next/link";

import { Button } from "@/components/ui";
import { fanPageCtas } from "@/lib/own-fan-ctas";

type FanCtas = ReturnType<typeof fanPageCtas>;

type Props = {
  isOwnPassport?: boolean;
  displayName?: string;
  sharePath?: string | null;
  ctas?: FanCtas;
};

export function FanPassportCTA({
  isOwnPassport = false,
  displayName,
  sharePath = null,
  ctas,
}: Props) {
  const name = displayName?.trim() || "this fan";
  const resolved =
    ctas ?? fanPageCtas(isOwnPassport ? "own_passport" : "visitor");

  return (
    <section className="rounded-[var(--radius-xl)] border border-border bg-gradient-to-br from-card via-card to-surface-muted px-5 py-7 sm:px-8 sm:py-8">
      <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
        Fan Passport
      </p>
      <h2 className="mt-2 max-w-2xl text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
        {isOwnPassport
          ? (resolved.title ?? "This is your Fan Passport")
          : `Connect with ${name} — shared nights, hosts, and scenes stay on Pàdéyá.`}
      </h2>
      {isOwnPassport && resolved.description ? (
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          {resolved.description}
        </p>
      ) : null}
      <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {isOwnPassport ? (
          <>
            {resolved.primary ? (
              <Link href={resolved.primary.href}>
                <Button>{resolved.primary.label}</Button>
              </Link>
            ) : null}
            {resolved.secondary ? (
              <Link href={resolved.secondary.href}>
                <Button variant="secondary">{resolved.secondary.label}</Button>
              </Link>
            ) : null}
            {resolved.allowShare && resolved.share && sharePath ? (
              <Link href={sharePath} target="_blank" rel="noreferrer">
                <Button variant="secondary">{resolved.share.label}</Button>
              </Link>
            ) : null}
          </>
        ) : (
          <>
            {resolved.showConnectionRequest ? (
              <Link href="/connect">
                <Button>Fan Connect</Button>
              </Link>
            ) : null}
            <Link href="/register">
              <Button variant="secondary">Create your Fan Passport</Button>
            </Link>
          </>
        )}
      </div>
    </section>
  );
}
