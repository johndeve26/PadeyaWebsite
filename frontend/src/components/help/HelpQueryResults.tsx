"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { HelpArticleCard } from "@/components/help/HelpArticleCard";
import { EmptyState } from "@/components/ui";
import { HELP_GROUP_LABELS, type HelpArticleListItem } from "@/lib/knowledge-base/api";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";

function groupSearchHits(hits: HelpArticleListItem[]) {
  const map = new Map<string, HelpArticleListItem[]>();
  for (const article of hits) {
    const key = article.category?.group_key || article.category?.name || "general";
    const list = map.get(key) || [];
    list.push(article);
    map.set(key, list);
  }
  return map;
}

/**
 * Client search / audience facets for /help — keeps the RSC page free of
 * `searchParams` so the default Help Center stays CDN-cacheable.
 */
export function HelpQueryResults() {
  const searchParams = useSearchParams();
  const q = (searchParams.get("q") || "").trim();
  const audience = (searchParams.get("audience") || "").trim();
  const [hits, setHits] = useState<HelpArticleListItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!q && !audience) {
      setHits([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (audience && !q) qs.set("audience", audience);
    qs.set("limit", q ? "30" : "20");
    const root = `${getApiBaseUrl() || ""}${getApiPrefix()}`;
    void fetch(`${root}/help/articles?${qs}`)
      .then(async (res) => {
        if (!res.ok) return [] as HelpArticleListItem[];
        return (await res.json()) as HelpArticleListItem[];
      })
      .then((rows) => {
        if (!cancelled) setHits(rows);
      })
      .catch(() => {
        if (!cancelled) setHits([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [q, audience]);

  const grouped = useMemo(
    () => (q ? groupSearchHits(hits) : null),
    [q, hits],
  );

  if (!q && !audience) return null;

  if (q) {
    return (
      <section className="mt-14">
        <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading">
          Results for &ldquo;{q}&rdquo;
        </h2>
        {loading ? (
          <p className="mt-6 text-sm text-muted-foreground">Searching…</p>
        ) : hits.length && grouped ? (
          <div className="mt-8 space-y-12">
            {[...grouped.entries()].map(([group, articles]) => (
              <div key={group}>
                <h3 className="font-display text-lg font-extrabold text-heading">
                  {HELP_GROUP_LABELS[group] || group}
                </h3>
                <div className="mt-5 grid gap-8 sm:grid-cols-2">
                  {articles.map((a) => (
                    <HelpArticleCard key={a.id} article={a} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-8">
            <EmptyState
              title="No answer found. Open a support ticket."
              description="Try a shorter query, browse categories below, or open Support with your topic."
              action={
                <Link href="/support" className="text-sm font-semibold text-primary-text">
                  Open support ticket
                </Link>
              }
            />
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="mt-14">
      <h2 className="font-display text-2xl font-extrabold tracking-tight text-heading capitalize">
        {HELP_GROUP_LABELS[audience] || `${audience} guides`}
      </h2>
      {loading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading…</p>
      ) : hits.length ? (
        <div className="mt-8 grid gap-8 sm:grid-cols-2">
          {hits.map((a) => (
            <HelpArticleCard key={a.id} article={a} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
