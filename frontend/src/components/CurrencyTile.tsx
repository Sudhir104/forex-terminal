import Link from "next/link";
import { CurrencyScore } from "@/lib/api";
import { ScoreBadge } from "./ScoreBadge";

export function CurrencyTile({ score }: { score: CurrencyScore }) {
  return (
    <Link
      href={`/currencies/${score.currency}`}
      className="flex items-center justify-between rounded-md border border-line bg-panel px-4 py-3 transition-colors hover:border-gold/50 hover:bg-panel2"
    >
      <div>
        <div className="font-mono text-sm font-semibold tracking-wide text-ink">{score.currency}</div>
        <div className="text-[11px] text-muted">{score.coverage < 0.5 ? "thin data" : `${score.confidence} confidence`}</div>
      </div>
      <ScoreBadge value={score.total} />
    </Link>
  );
}
