"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, CalEvent } from "@/lib/api";
import { Panel } from "@/components/Panel";
import { EventRow } from "@/components/EventRow";

export default function CalendarPage() {
  const { email } = useAuth();
  const [events, setEvents] = useState<CalEvent[] | null>(null);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    if (!email) return;
    api.calendar().then(setEvents).catch(() => setEvents([]));
  }, [email]);

  if (!email) return null;

  const filtered = (events || []).filter((e) => !filter || e.currency === filter);
  const grouped = filtered.reduce<Record<string, CalEvent[]>>((acc, e) => {
    (acc[e.event_date] ||= []).push(e);
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <header>
        <h1 className="text-lg font-semibold text-ink">Economic calendar</h1>
        <p className="text-sm text-muted">High-impact releases and central-bank meeting dates for the next few weeks.</p>
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

      {events === null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : Object.keys(grouped).length === 0 ? (
        <p className="text-sm text-muted">No events on file yet — run the calendar collector.</p>
      ) : (
        Object.entries(grouped)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([date, rows]) => (
            <Panel key={date} title={date}>
              <div>{rows.map((e) => <EventRow key={e.id} e={e} />)}</div>
            </Panel>
          ))
      )}
    </div>
  );
}
