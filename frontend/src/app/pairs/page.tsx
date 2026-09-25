"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api, Pair, PairExplain } from "@/lib/api";
import { Panel } from "@/components/Panel";
import { ScoreBadge } from "@/components/ScoreBadge";
import { fmtPrice, timeAgo } from "@/lib/format";

const MAJORS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "NZD/USD", "EUR/GBP", "EUR/JPY", "AUD/NZD"];
const CCY = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"];

export default function PairsPage() {
  const { email } = useAuth();
  const router = useRouter();
  const [pair, setPair] = useState("EUR/USD");
  const [data, setData] = useState<Pair | null>(null);
  const [explain, setExplain] = useState<PairExplain | null>(null);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [base, quote] = pair.split("/");

  useEffect(() => {
    if (!email) return;
    setData(null);
    setExplain(null);
    api.pair(pair).then(setData).catch(() => setData(null));
  }, [email, pair]);

  async function loadWhy() {
    setLoadingExplain(true);
    try {
      setExplain(await api.explainPair(pair));
    } finally {
      setLoadingExplain(false);
    }
  }

  if (!email) return null;

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <header>
        <h1 className="text-lg font-semibold text-ink">Pair analyzer</h1>
        <p className="text-sm text-muted">Compare the fundamental strength behind any two of the eight major currencies.</p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={base}
          onChange={(e) => setPair(`${e.target.value}/${quote === e.target.value ? CCY.find((c) => c !== e.target.value) : quote}`)}
          className="rounded border border-line bg-panel2 px-2 py-1.5 font-mono text-sm text-ink"
        >
          {CCY.map((c) => <option key={c}>{c}</option>)}
        </select>
        <span className="text-muted">/</span>
        <select
          value={quote}
          onChange={(e) => setPair(`${base === e.target.value ? CCY.find((c) => c !== e.target.value) : base}/${e.target.value}`)}
          className="rounded border border-line bg-panel2 px-2 py-1.5 font-mono text-sm text-ink"
        >
          {CCY.map((c) => <option key={c}>{c}</option>)}
        </select>
        <div className="ml-auto flex flex-wrap gap-1.5">
          {MAJORS.map((m) => (
            <button
              key={m}
              onClick={() => setPair(m)}
              className={`rounded border px-2 py-1 font-mono text-xs ${pair === m ? "border-gold text-gold" : "border-line text-muted hover:text-ink"}`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {data && (
        <>
          <Panel>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="font-mono text-xl font-bold text-ink">{data.pair}</div>
                {data.price ? (
                  <div className="mt-1 font-mono text-sm text-muted">
                    {fmtPrice(data.price.mid, data.pair)} · {data.price.is_reference ? "reference rate" : "live"} · {timeAgo(data.price.ts)}
                  </div>
                ) : (
                  <div className="mt-1 text-sm text-muted">No price yet</div>
                )}
              </div>
              <div className="text-right">
                <div className="text-[11px] text-muted">Fundamental differential</div>
                <div className="font-mono text-xl font-bold text-ink">
                  {data.differential === null ? "—" : `${data.differential > 0 ? "+" : ""}${data.differential.toFixed(2)}`}
                </div>
              </div>
            </div>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2">
            {[data.base_score, data.quote_score].map((s) => (
              <button key={s.currency} onClick={() => router.push(`/currencies/${s.currency}`)} className="text-left">
                <Panel title={s.currency} right={<ScoreBadge value={s.total} />}>
                  <div className="space-y-2">
                    {s.factors
                      .filter((f) => f.score !== null)
                      .sort((a, b) => Math.abs((b.score ?? 5) - 5) - Math.abs((a.score ?? 5) - 5))
                      .slice(0, 4)
                      .map((f) => (
                        <div key={f.factor} className="flex items-center justify-between text-xs">
                          <span className="text-muted">{f.label}</span>
                          <span className="font-mono text-ink">{f.score!.toFixed(1)}</span>
                        </div>
                      ))}
                  </div>
                </Panel>
              </button>
            ))}
          </div>

          <Panel
            title="Why?"
            right={
              !explain && (
                <button onClick={loadWhy} disabled={loadingExplain} className="text-xs text-gold hover:opacity-80 disabled:opacity-50">
                  {loadingExplain ? "Explaining…" : "Explain this differential"}
                </button>
              )
            }
          >
            {explain ? <p className="text-sm text-ink">{explain.text}</p> : <p className="text-sm text-muted">Not a guaranteed trading direction — an analytical signal from the model above.</p>}
          </Panel>
        </>
      )}
    </div>
  );
}
