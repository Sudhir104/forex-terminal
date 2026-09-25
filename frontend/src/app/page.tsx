"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api, CurrencyScore, NewsItem, CalEvent } from "@/lib/api";
import { CurrencyTile } from "@/components/CurrencyTile";
import { Panel } from "@/components/Panel";
import { NewsRow } from "@/components/NewsRow";
import { EventRow } from "@/components/EventRow";

export default function HomePage() {
  const { email } = useAuth();
  const [scores, setScores] = useState<CurrencyScore[] | null>(null);
  const [news, setNews] = useState<NewsItem[] | null>(null);
  const [events, setEvents] = useState<CalEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!email) return;
    let cancelled = false;
    async function load() {
      try {
        const [s, n, e] = await Promise.all([api.currencies(), api.news(undefined, 48), api.calendar()]);
        if (cancelled) return;
        setScores([...s].sort((a, b) => (b.total ?? -1) - (a.total ?? -1)));
        setNews(n.slice(0, 8));
        setEvents(e.filter((ev) => new Date(ev.event_date) >= new Date(new Date().toDateString())).slice(0, 6));
      } catch {
        if (!cancelled) setError("Could not reach the backend API. Is it running and is NEXT_PUBLIC_API_URL set?");
      }
    }
    load();
    const id = setInterval(load, 60_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [email]);

  if (!email) return null;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-lg font-semibold text-ink">Currency strength</h1>
        <p className="text-sm text-muted">Ranked strongest to weakest. Tap a currency for the full factor breakdown.</p>
      </header>

      {error && <p className="rounded border border-neg/40 bg-neg/10 px-3 py-2 text-sm text-neg">{error}</p>}

      {!scores ? (
        <SkeletonGrid />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {scores.map((s) => (
            <CurrencyTile key={s.currency} score={s} />
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Upcoming events" right={<Link href="/calendar" className="text-xs text-steel hover:text-ink">View calendar →</Link>}>
          {events === null ? (
            <p className="text-sm text-muted">Loading…</p>
          ) : events.length === 0 ? (
            <p className="text-sm text-muted">No events in the window yet — the calendar collector may not have run.</p>
          ) : (
            <div>{events.map((e) => <EventRow key={e.id} e={e} />)}</div>
          )}
        </Panel>

        <Panel title="Latest fundamental news" right={<Link href="/news" className="text-xs text-steel hover:text-ink">View all →</Link>}>
          {news === null ? (
            <p className="text-sm text-muted">Loading…</p>
          ) : news.length === 0 ? (
            <p className="text-sm text-muted">No tagged headlines yet — the news collector may not have run.</p>
          ) : (
            <div>{news.map((n) => <NewsRow key={n.id} item={n} />)}</div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="h-[60px] animate-pulse rounded-md border border-line bg-panel" />
      ))}
    </div>
  );
}
