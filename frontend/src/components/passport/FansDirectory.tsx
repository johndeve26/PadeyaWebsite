"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { FanPassportCard } from "@/components/passport/FanPassportCard";
import {
  Badge,
  Button,
  Container,
  EmptyState,
  Input,
  Select,
  SkeletonLoader,
} from "@/components/ui";
import {
  trackFanDirectoryFilterUsed,
  trackFanDirectorySearch,
  trackFanDirectoryView,
} from "@/lib/analytics";
import { isOwnFanPassport } from "@/lib/own-fan-ctas";
import { fetchFanDirectory } from "@/lib/passport-api";
import type { FanDirectoryCard } from "@/lib/types/passport";

const SORTS = [
  { value: "recently_active", label: "Recently active" },
  { value: "most_badges", label: "Most badges" },
  { value: "most_events", label: "Most events attended" },
  { value: "most_reviews", label: "Most reviews" },
  { value: "newest", label: "Newest Passports" },
];

const PROOF = [
  "Verified check-ins",
  "Fan badges",
  "Followed hosts",
  "Vault unlocks",
  "Public Passports only",
];

export function FansDirectory() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [city, setCity] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("recently_active");
  const [hasReviews, setHasReviews] = useState<"any" | "yes">("any");
  const [refreshKey, setRefreshKey] = useState(0);
  const [items, setItems] = useState<FanDirectoryCard[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    trackFanDirectoryView();
  }, []);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const res = await fetchFanDirectory({
            q: q.trim() || undefined,
            city: city.trim() || undefined,
            category: category.trim() || undefined,
            sort,
            has_reviews: hasReviews === "yes" ? true : undefined,
            limit: 24,
          });
          if (!active) return;
          setItems(res.items);
          setTotal(res.total);
          setError(null);
        } catch {
          if (!active) return;
          setError("Could not load the Fan Passport Directory.");
          setItems([]);
          setTotal(0);
        } finally {
          if (active) setLoading(false);
        }
      })();
    }, 200);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [q, city, category, sort, hasReviews, refreshKey]);

  const cities = useMemo(() => {
    const set = new Set<string>();
    for (const f of items) {
      if (f.city_label) set.add(f.city_label);
    }
    return [...set].sort();
  }, [items]);

  return (
    <div className="bg-background">
      <section className="relative overflow-hidden border-b border-border bg-surface">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 padeya-hero-glow opacity-70"
        />
        <Container className="relative space-y-6 py-12 sm:py-16">
          <Badge tone="accent">Fan Passport Directory</Badge>
          <div className="max-w-3xl space-y-3">
            <h1 className="text-3xl font-extrabold tracking-tight text-heading sm:text-5xl">
              Fan Passports built from real nights.
            </h1>
            <p className="text-base leading-relaxed text-muted-foreground sm:text-lg">
              Explore public Fan Passports on Pàdéyá — attendance proof, badges,
              followed hosts, and optional Fan Connect. Visibility is always
              opt-in.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <a href="#directory">
              <Button size="lg">Explore public Passports</Button>
            </a>
            <Link href="/dashboard/passport/settings">
              <Button size="lg" variant="secondary">
                Create your Passport
              </Button>
            </Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {PROOF.map((chip) => (
              <Badge key={chip} tone="outline" size="sm">
                {chip}
              </Badge>
            ))}
          </div>
        </Container>
      </section>

      <Container id="directory" className="space-y-8 py-10 sm:py-12">
        <form
          className="grid gap-3 rounded-[var(--radius-lg)] border border-border bg-card p-4 dark:bg-surface-elevated sm:grid-cols-2 lg:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            if (q.trim()) trackFanDirectorySearch({ qLength: q.trim().length });
            setLoading(true);
            setRefreshKey((k) => k + 1);
          }}
        >
          <Input
            label="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Display name or @username"
            className="lg:col-span-2"
          />
          <Input
            label="City"
            value={city}
            onChange={(e) => {
              setCity(e.target.value);
              if (e.target.value)
                trackFanDirectoryFilterUsed({
                  filterType: "city",
                  value: e.target.value.slice(0, 40),
                });
            }}
            placeholder={cities[0] || "Lagos"}
            list="fan-dir-cities"
          />
          <datalist id="fan-dir-cities">
            {cities.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
          <Input
            label="Scene / category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              if (e.target.value)
                trackFanDirectoryFilterUsed({
                  filterType: "category",
                  value: e.target.value.slice(0, 40),
                });
            }}
            placeholder="Music, comedy…"
          />
          <Select
            label="Sort"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              trackFanDirectoryFilterUsed({
                filterType: "sort",
                value: e.target.value,
              });
            }}
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Select>
          <Select
            label="Reviews"
            value={hasReviews}
            onChange={(e) => {
              setHasReviews(e.target.value as "any" | "yes");
              trackFanDirectoryFilterUsed({
                filterType: "has_reviews",
                value: e.target.value,
              });
            }}
            className="lg:col-span-2"
          >
            <option value="any">Any public reviews</option>
            <option value="yes">Has public reviews</option>
          </Select>
          <div className="flex items-end lg:col-span-3">
            <Button type="submit" className="w-full sm:w-auto">
              Apply
            </Button>
          </div>
        </form>

        <p className="text-sm text-muted-foreground">
          {loading
            ? "Loading public Fan Passports…"
            : `${total} public Passport${total === 1 ? "" : "s"} · opt-in only`}
        </p>

        {error ? (
          <p className="text-sm font-semibold text-danger">{error}</p>
        ) : null}

        {loading ? <SkeletonLoader lines={6} /> : null}

        {!loading && items.length === 0 ? (
          <EmptyState
            title="No public Fan Passports yet"
            description="Fans can choose to make their Passport visible from their privacy settings."
            action={
              <Link href="/dashboard/passport/settings">
                <Button>Create your Passport</Button>
              </Link>
            }
          />
        ) : null}

        {!loading && items.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((fan) => (
              <FanPassportCard
                key={fan.username}
                fan={fan}
                isOwnPassport={isOwnFanPassport(user?.id, fan.user_id)}
              />
            ))}
          </div>
        ) : null}
      </Container>
    </div>
  );
}
