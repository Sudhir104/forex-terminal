"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, NewsItem } from "@/lib/api";
import { Panel } from "@/components/Panel";
import { NewsRow } from "@/components/NewsRow";

export default function NewsPage() {
  const { email } = useAuth();
  const [news, setNews] = useState<NewsItem[] | null>(null);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    if (!email) return;
    api.news(undefined, 24 * 7).then(setNews).catch(() => setNews([]));
  }, [email]);

  if (!email) return null;
  const filtered = (news || []).filter((n) => !filter || n.currency === filter);

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <header>
        <h1 className="text-lg font-semibold text-ink">Fundamental news</h1>
        <p className="text-sm text-muted">Tagged headlines from official central-bank and statistics-agency feeds, last 7 days.</p>
      </header>

      <div className="flex flex-wrap gap-1.5">
        <button onClick={() => setFilter(null)} className={`rounded border px-2 py-1 font-mono text-xs ${!filter ? "border-gold text-gold" : "border-line text-muted"}`}>
          ALL
        </button>
        {["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"].map((c) => (
          <button key={c} onClick={() => setFilter(c)} className={`rounded border px-2 py-1 font-mono text-xs ${filter === c ? "border-gold text-gold" : "border-line text-muted"}`}>
            {c}
          </button>
        ))}
      </div>

      <Panel>
        {news === null ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted">No tagged news yet — run the news collector.</p>
        ) : (
          <div>{filtered.map((n) => <NewsRow key={n.id} item={n} />)}</div>
        )}
      </Panel>
    </div>
  );
}
