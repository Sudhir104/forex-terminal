import { fmtScore, scoreTone } from "@/lib/format";

const TONE_CLASSES: Record<string, string> = {
  pos: "text-pos border-pos/40 bg-pos/10",
  neg: "text-neg border-neg/40 bg-neg/10",
  neutral: "text-steel border-steel/40 bg-steel/10",
};

export function ScoreBadge({ value, size = "md" }: { value: number | null; size?: "sm" | "md" | "lg" }) {
  const tone = scoreTone(value);
  const sizeCls = size === "lg" ? "text-3xl px-3 py-1.5" : size === "sm" ? "text-sm px-1.5 py-0.5" : "text-lg px-2 py-1";
  return (
    <span className={`inline-flex items-baseline gap-1 rounded border font-mono tabular-nums ${TONE_CLASSES[tone]} ${sizeCls}`}>
      {fmtScore(value)}
      <span className="text-[0.6em] opacity-70">/10</span>
    </span>
  );
}

export function ImpactPill({ impact }: { impact: string }) {
  const cls =
    impact === "high" ? "bg-neg/15 text-neg border-neg/40" : impact === "medium" ? "bg-gold/15 text-gold border-gold/40" : "bg-steel/15 text-steel border-steel/40";
  return <span className={`rounded border px-1.5 py-0.5 text-[11px] font-medium ${cls}`}>{impact}</span>;
}

export function ConfidencePill({ confidence, coverage }: { confidence: string; coverage: number }) {
  return (
    <span className="text-[11px] text-muted" title={`${Math.round(coverage * 100)}% of scoring factors have data`}>
      {confidence} confidence · {Math.round(coverage * 100)}% coverage
    </span>
  );
}
