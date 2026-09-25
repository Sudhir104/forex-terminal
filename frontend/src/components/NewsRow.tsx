import { NewsItem } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { ImpactPill } from "./ScoreBadge";

export function NewsRow({ item }: { item: NewsItem }) {
  const toneCls = item.tone > 0.15 ? "text-pos" : item.tone < -0.15 ? "text-neg" : "text-muted";
  return (
    <a
      href={item.source_url}
      target="_blank"
      rel="noreferrer"
      className="flex flex-col gap-1 border-b border-line py-3 last:border-none hover:bg-panel2/60"
    >
      <div className="flex items-center gap-2 text-[11px] text-muted">
        <span className="font-mono font-semibold text-gold">{item.currency}</span>
        <ImpactPill impact={item.impact} />
        <span>{item.category.replace("_", " ")}</span>
        <span className="ml-auto">{timeAgo(item.published_at)}</span>
      </div>
      <div className="text-sm text-ink">{item.headline}</div>
      <div className="flex items-center gap-2 text-[11px] text-muted">
        <span>{item.source}</span>
        <span className={toneCls}>tone {item.tone > 0 ? "+" : ""}{item.tone.toFixed(2)}</span>
      </div>
    </a>
  );
}
