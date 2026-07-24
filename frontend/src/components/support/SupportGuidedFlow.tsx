"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { SupportTicketForm } from "@/components/support/SupportTicketForm";
import { HelpSearch } from "@/components/help/HelpSearch";
import {
  Alert,
  Button,
  Container,
  SkeletonLoader,
} from "@/components/ui";
import { track } from "@/lib/analytics";
import { brand } from "@/lib/brand";
import { apiRequest } from "@/lib/api";
import type { HelpArticleListItem } from "@/lib/knowledge-base/api";
import { fetchHelpArticles } from "@/lib/knowledge-base/api";
import { postSupportDeflectionEvent } from "@/lib/support-api";
import {
  getSupportTopicGuide,
  SUPPORT_TOPIC_GUIDES,
} from "@/lib/support-topics";
import { userHasRole } from "@/lib/auth/permissions";

type Step = "topics" | "guide" | "ticket";

function sessionKey(): string {
  if (typeof window === "undefined") return "";
  const key = "padeya_support_deflection_session";
  let value = window.sessionStorage.getItem(key);
  if (!value) {
    value = crypto.randomUUID().replace(/-/g, "").slice(0, 32);
    window.sessionStorage.setItem(key, value);
  }
  return value;
}

export function SupportGuidedFlow() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTopic = searchParams.get("topic") || "";
  const forceTicket = searchParams.get("ticket") === "1";
  const q = (searchParams.get("q") || "").trim();

  const [step, setStep] = useState<Step>(() =>
    forceTicket && initialTopic ? "ticket" : initialTopic ? "guide" : "topics",
  );
  const [topic, setTopic] = useState(initialTopic);
  const [articles, setArticles] = useState<HelpArticleListItem[]>([]);
  const [loadingArticles, setLoadingArticles] = useState(false);
  const [clickedSlugs, setClickedSlugs] = useState<string[]>([]);
  const [searchHits, setSearchHits] = useState<HelpArticleListItem[]>([]);
  const [pending, startTransition] = useTransition();

  const guide = useMemo(() => getSupportTopicGuide(topic), [topic]);
  const isHost = Boolean(user && userHasRole(user, "host"));
  const role: "guest" | "fan" | "host" = !user
    ? "guest"
    : isHost
      ? "host"
      : "fan";

  useEffect(() => {
    if (!q) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear search
      setSearchHits([]);
      return;
    }
    let active = true;
    void (async () => {
      try {
        const hits = await fetchHelpArticles({ q, limit: 8 });
        if (active) setSearchHits(hits);
      } catch {
        if (active) setSearchHits([]);
      }
    })();
    return () => {
      active = false;
    };
  }, [q]);

  useEffect(() => {
    if (!topic || step === "topics") return;
    let active = true;
    void (async () => {
      setLoadingArticles(true);
      try {
        const res = await apiRequest<{
          topic: string;
          articles: HelpArticleListItem[];
        }>(`/help/suggestions?topic=${encodeURIComponent(topic)}&limit=5`, {
          auth: false,
        });
        if (!active) return;
        setArticles(res.articles || []);
        const sk = sessionKey();
        track("support_help_articles_shown", {
          metadata: { topic, count: String(res.articles?.length || 0) },
        });
        void postSupportDeflectionEvent({
          event_type: "support_help_articles_shown",
          topic,
          session_key: sk,
          meta: { count: res.articles?.length || 0 },
        });
      } catch {
        if (active) setArticles([]);
      } finally {
        if (active) setLoadingArticles(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [topic, step]);

  function selectTopic(value: string) {
    setTopic(value);
    setClickedSlugs([]);
    setStep("guide");
    const sk = sessionKey();
    track("support_topic_selected", { metadata: { topic: value } });
    void postSupportDeflectionEvent({
      event_type: "support_topic_selected",
      topic: value,
      session_key: sk,
    });
    startTransition(() => {
      router.replace(`/support?topic=${encodeURIComponent(value)}`, {
        scroll: false,
      });
    });
  }

  function solved() {
    const sk = sessionKey();
    track("support_issue_solved_without_ticket", {
      metadata: { topic },
    });
    void postSupportDeflectionEvent({
      event_type: "support_issue_solved_without_ticket",
      topic,
      session_key: sk,
    });
    startTransition(() => {
      router.push("/help");
    });
  }

  function openTicket() {
    setStep("ticket");
    const sk = sessionKey();
    track("support_ticket_started_after_help", { metadata: { topic } });
    void postSupportDeflectionEvent({
      event_type: "support_ticket_started_after_help",
      topic,
      session_key: sk,
      meta: { articles: articles.map((a) => a.slug).join(",") },
    });
    startTransition(() => {
      router.replace(
        `/support?topic=${encodeURIComponent(topic)}&ticket=1`,
        { scroll: false },
      );
    });
  }

  function onArticleClick(slug: string, id: string) {
    setClickedSlugs((prev) => (prev.includes(slug) ? prev : [...prev, slug]));
    const sk = sessionKey();
    track("support_article_clicked", {
      metadata: { topic, article_slug: slug },
    });
    void postSupportDeflectionEvent({
      event_type: "support_article_clicked",
      topic,
      session_key: sk,
      article_id: id,
      article_slug: slug,
    });
  }

  const selfService = (guide?.selfService || []).filter(
    (link) => !link.roles || link.roles.includes(role),
  );

  return (
    <div className="space-y-10">
      <section className="mx-auto max-w-3xl text-center">
        <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary">
          {brand.name}
        </p>
        <h1 className="mt-3 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
          Support for fans, hosts, and visitors
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          Search Help or pick a topic first. We&apos;ll suggest answers and
          self-service links before you open a tracked ticket.
        </p>
        <div className="mx-auto mt-8 max-w-2xl text-left">
          <HelpSearch
            initialQuery={q}
            actionHref="/support"
          />
        </div>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          <Link href="/help">
            <Button size="lg" variant="secondary">
              Browse Help Center
            </Button>
          </Link>
          <Link href="/support/tickets/lookup">
            <Button size="lg" variant="ghost">
              Track a ticket
            </Button>
          </Link>
          {user ? (
            <Link href={isHost ? "/host/support" : "/dashboard/support"}>
              <Button size="lg" variant="ghost">
                My tickets
              </Button>
            </Link>
          ) : (
            <Link href="/login?next=/dashboard/support">
              <Button size="lg" variant="ghost">
                Sign in
              </Button>
            </Link>
          )}
        </div>
      </section>

      {q ? (
        <section className="mx-auto max-w-3xl">
          <h2 className="text-xl font-extrabold text-foreground">
            Help results for &ldquo;{q}&rdquo;
          </h2>
          {searchHits.length ? (
            <ul className="mt-4 space-y-3">
              {searchHits.map((a) => (
                <li key={a.id}>
                  <Link
                    href={`/help/articles/${a.slug}`}
                    className="block border-b border-border py-3 font-semibold text-heading hover:text-primary-text"
                    onClick={() => onArticleClick(a.slug, a.id)}
                  >
                    {a.title}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">
              No answer found. Pick a topic below or open a ticket after
              reviewing suggestions.
            </p>
          )}
        </section>
      ) : null}

      {step === "topics" || !topic ? (
        <section className="mx-auto max-w-4xl">
          <div className="mb-6 text-center">
            <h2 className="text-2xl font-extrabold text-foreground sm:text-3xl">
              Choose a topic
            </h2>
            <p className="mt-2 text-muted-foreground">
              We&apos;ll show Help articles and self-service links before the
              ticket form.
            </p>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {SUPPORT_TOPIC_GUIDES.map((cat) => (
              <li key={cat.value}>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => selectTopic(cat.value)}
                  className="group flex h-full w-full flex-col justify-between rounded-[var(--radius-lg)] border border-border bg-card/80 px-4 py-4 text-left transition-[border-color,background-color,transform] hover:border-primary/40 hover:bg-card hover:-translate-y-0.5 dark:bg-surface-elevated/80"
                >
                  <span className="text-base font-bold text-foreground group-hover:text-primary">
                    {cat.label}
                  </span>
                  <span className="mt-3 text-sm font-semibold text-muted-foreground">
                    View help →
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {step === "guide" && guide ? (
        <section className="mx-auto max-w-3xl space-y-8">
          <div>
            <button
              type="button"
              className="text-sm font-semibold text-primary-text"
              onClick={() => {
                setStep("topics");
                setTopic("");
                router.replace("/support", { scroll: false });
              }}
            >
              ← All topics
            </button>
            <h2 className="mt-3 text-2xl font-extrabold text-foreground sm:text-3xl">
              {guide.label}
            </h2>
            <p className="mt-2 text-muted-foreground">{guide.explanation}</p>
          </div>

          {guide.safetyWarning ? (
            <Alert tone="warning" title="Safety first">
              {guide.safetyWarning}
            </Alert>
          ) : null}

          <div>
            <h3 className="text-lg font-extrabold text-heading">
              Related Help articles
            </h3>
            {loadingArticles ? (
              <div className="mt-3">
                <SkeletonLoader lines={3} />
              </div>
            ) : articles.length ? (
              <ul className="mt-3 space-y-2">
                {articles.map((a) => (
                  <li key={a.id}>
                    <Link
                      href={`/help/articles/${a.slug}`}
                      className="block border-b border-border py-3 font-semibold text-heading hover:text-primary-text"
                      onClick={() => onArticleClick(a.slug, a.id)}
                    >
                      {a.title}
                    </Link>
                    {a.excerpt ? (
                      <p className="pb-2 text-sm text-muted-foreground">
                        {a.excerpt}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <ul className="mt-3 space-y-2">
                {guide.fallbackArticleSlugs.map((slug) => (
                  <li key={slug}>
                    <Link
                      href={`/help/articles/${slug}`}
                      className="block border-b border-border py-3 font-semibold text-heading hover:text-primary-text"
                      onClick={() => onArticleClick(slug, slug)}
                    >
                      {slug.replace(/-/g, " ")}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h3 className="text-lg font-extrabold text-heading">
              Quick answers
            </h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted-foreground sm:text-base">
              {guide.quickAnswers.map((answer) => (
                <li key={answer}>{answer}</li>
              ))}
            </ul>
          </div>

          {selfService.length ? (
            <div>
              <h3 className="text-lg font-extrabold text-heading">
                Self-service
              </h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {selfService.map((link) => (
                  <Link key={link.href + link.label} href={link.href}>
                    <Button size="sm" variant="secondary">
                      {link.label}
                    </Button>
                  </Link>
                ))}
              </div>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3 border-t border-border pt-6">
            <Button onClick={solved} variant="secondary">
              This solved my issue
            </Button>
            <Button onClick={openTicket}>
              I still need help — open ticket
            </Button>
          </div>
        </section>
      ) : null}

      {step === "ticket" && topic ? (
        <section className="mx-auto max-w-2xl space-y-4">
          <button
            type="button"
            className="text-sm font-semibold text-primary-text"
            onClick={() => {
              setStep("guide");
              router.replace(`/support?topic=${encodeURIComponent(topic)}`, {
                scroll: false,
              });
            }}
          >
            ← Back to suggestions
          </button>
          <h2 className="text-2xl font-extrabold text-foreground">
            Open a support ticket
          </h2>
          <p className="text-muted-foreground">
            Topic prefilled as{" "}
            <span className="font-semibold text-foreground">
              {guide?.label || topic}
            </span>
            . Include order or event references when you can.
          </p>
          <SupportTicketForm
            requesterContext={role === "host" ? "host" : role === "guest" ? "visitor" : "fan"}
            initialCategory={topic}
            deflection={{
              topic,
              suggested_article_ids: articles.map((a) => a.id),
              suggested_article_slugs: articles.map((a) => a.slug),
              articles_clicked: clickedSlugs,
              referrer:
                typeof document !== "undefined" ? document.referrer || undefined : undefined,
              session_key: sessionKey(),
              help_suggestions_shown: true,
            }}
            successHrefForTicket={(id) =>
              role === "host" ? `/host/support/${id}` : `/dashboard/support/${id}`
            }
          />
        </section>
      ) : null}
    </div>
  );
}

export function SupportGuidedFlowPage() {
  return (
    <div className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_color-mix(in_srgb,var(--primary)_18%,transparent),_transparent_55%),linear-gradient(180deg,var(--surface-muted),var(--background))]"
      />
      <Container className="py-12 sm:py-16 lg:py-20">
        <SupportGuidedFlow />
      </Container>
    </div>
  );
}
