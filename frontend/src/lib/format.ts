export function fmtScore(v: number | null): string {
  return v === null ? "—" : v.toFixed(2);
}
export function fmtPrice(v: number, pair: string): string {
  const decimals = pair.startsWith("USD/JPY") || pair.includes("JPY") ? 3 : 5;
  return v.toFixed(decimals);
}
export function scoreTone(v: number | null): "pos" | "neg" | "neutral" {
  if (v === null) return "neutral";
  if (v >= 5.5) return "pos";
  if (v <= 4.5) return "neg";
  return "neutral";
}
export function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const diffMin = Math.round((Date.now() - then) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const h = Math.round(diffMin / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}
