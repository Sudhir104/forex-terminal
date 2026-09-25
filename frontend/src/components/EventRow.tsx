import { CalEvent } from "@/lib/api";
import { ImpactPill } from "./ScoreBadge";

export function EventRow({ e }: { e: CalEvent }) {
  const time = e.event_time ? new Date(e.event_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", timeZone: "UTC" }) + " UTC" : null;
  return (
    <div className="flex items-center gap-3 border-b border-line py-2.5 last:border-none">
      <div className="w-16 shrink-0 font-mono text-xs text-muted">{time || e.event_date}</div>
      <span className="font-mono text-xs font-semibold text-gold">{e.currency}</span>
      <span className="flex-1 text-sm text-ink">{e.title}</span>
      {(e.actual || e.forecast || e.previous) && (
        <span className="hidden shrink-0 font-mono text-[11px] text-muted sm:inline">
          A {e.actual ?? "—"} / F {e.forecast ?? "—"} / P {e.previous ?? "—"}
        </span>
      )}
      <ImpactPill impact={e.impact} />
    </div>
  );
}
