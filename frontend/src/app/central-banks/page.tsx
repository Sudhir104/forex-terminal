"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, CentralBank } from "@/lib/api";
import { Panel } from "@/components/Panel";

const STANCE_CLASS: Record<string, string> = {
  hawkish: "text-neg border-neg/40 bg-neg/10",
  dovish: "text-pos border-pos/40 bg-pos/10",
  neutral: "text-steel border-steel/40 bg-steel/10",
};

export default function CentralBanksPage() {
  const { email } = useAuth();
  const [banks, setBanks] = useState<CentralBank[] | null>(null);

  useEffect(() => {
    if (!email) return;
    api.centralBanks().then(setBanks).catch(() => setBanks([]));
  }, [email]);

  if (!email) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <header>
        <h1 className="text-lg font-semibold text-ink">Central banks</h1>
        <p className="text-sm text-muted">Policy stance is curated by hand in <code className="font-mono">data/central_banks.yaml</code> — everything else comes from official rate data.</p>
      </header>

      {banks === null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {banks.map((b) => (
            <Panel key={b.currency} title={`${b.currency} · ${b.bank}`}>
              <div className="space-y-1.5 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted">Policy rate</span>
                  <span className="font-mono text-ink">{b.policy_rate !== null ? `${b.policy_rate.toFixed(2)}%` : "—"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Stance</span>
                  <span className={`rounded border px-1.5 py-0.5 text-[11px] ${STANCE_CLASS[b.stance || ""] || "text-muted border-line"}`}>
                    {b.stance || "not assessed"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted">Next meeting</span>
                  <span className="font-mono text-ink">{b.next_meeting || "—"}</span>
                </div>
                {b.statement_url && (
                  <a href={b.statement_url} target="_blank" rel="noreferrer" className="inline-block pt-1 text-[11px] text-steel hover:text-ink">
                    Official statements →
                  </a>
                )}
              </div>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
