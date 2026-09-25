"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api, CurrencyScore, Explain } from "@/lib/api";
import { Panel } from "@/components/Panel";
import { ScoreBadge, ConfidencePill } from "@/components/ScoreBadge";
import { FactorBars } from "@/components/FactorBars";
import { timeAgo } from "@/lib/format";

export default function CurrencyPage() {
  const { email } = useAuth();
  const params = useParams<{ currency: string }>();
  const ccy = params.currency?.toUpperCase();
  const [score, setScore] = useState<CurrencyScore | null>(null);
  const [explain, setExplain] = useState<Explain | null>(null);
  const [loadingExplain, setLoadingExplain] = useState(false);

  useEffect(() => {
    if (!email || !ccy) return;
    api.currency(ccy).then(setScore).catch(() => setScore(null));
  }, [email, ccy]);

  async function loadWhy() {
    if (!ccy) return;
    setLoadingExplain(true);
    try {
      setExplain(await api.explainCurrency(ccy));
    } finally {
      setLoadingExplain(false);
    }
  }

  if (!email || !ccy) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold text-ink">{ccy}</h1>
          <p className="text-sm text-muted">
            {score ? <>Updated {timeAgo(score.computed_at)} · <ConfidencePill confidence={score.confidence} coverage={score.coverage} /></> : "Loading…"}
          </p>
        </div>
        {score && <ScoreBadge value={score.total} size="lg" />}
      </header>

      <Panel title="Factor breakdown">
        {score ? <FactorBars factors={score.factors} /> : <p className="text-sm text-muted">Loading…</p>}
      </Panel>

      <Panel
        title="Why?"
        right={
          !explain && (
            <button onClick={loadWhy} disabled={loadingExplain} className="text-xs text-gold hover:opacity-80 disabled:opacity-50">
              {loadingExplain ? "Explaining…" : "Explain this score"}
            </button>
          )
        }
      >
        {explain ? (
          <>
            <p className="text-sm text-ink">{explain.text}</p>
            <p className="mt-2 text-[11px] text-muted">
              {explain.origin === "llm" ? "AI-phrased from the factor data above." : "Generated directly from the factor data above."}
            </p>
          </>
        ) : (
          <p className="text-sm text-muted">Every score is traceable to the underlying data — tap the button to see it explained in plain language.</p>
        )}
      </Panel>
    </div>
  );
}
