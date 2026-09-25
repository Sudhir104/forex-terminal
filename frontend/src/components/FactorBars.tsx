import { Factor } from "@/lib/api";

export function FactorBars({ factors }: { factors: Factor[] }) {
  return (
    <div className="space-y-2.5">
      {factors.map((f) => (
        <div key={f.factor}>
          <div className="mb-1 flex items-baseline justify-between text-xs">
            <span className="text-ink">
              {f.label} {f.stale && <span className="ml-1 text-[10px] text-gold">stale</span>}
            </span>
            <span className="font-mono text-muted">{f.score === null ? "no data" : f.score.toFixed(1)}</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-panel2">
            {f.score !== null && (
              <div
                className={`h-1.5 rounded-full ${f.score >= 5.5 ? "bg-pos" : f.score <= 4.5 ? "bg-neg" : "bg-steel"}`}
                style={{ width: `${f.score * 10}%` }}
              />
            )}
          </div>
          {f.notes && <p className="mt-1 text-[11px] text-muted">{f.notes}</p>}
        </div>
      ))}
    </div>
  );
}
