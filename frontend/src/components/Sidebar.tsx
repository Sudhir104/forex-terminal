"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/pairs", label: "Pair analyzer" },
  { href: "/calendar", label: "Calendar" },
  { href: "/news", label: "News" },
  { href: "/central-banks", label: "Central banks" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { email, logout } = useAuth();
  if (!email) return null;
  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col border-r border-line bg-panel">
      <div className="border-b border-line px-4 py-4">
        <div className="font-mono text-sm font-bold tracking-tight text-gold">FX TERMINAL</div>
        <div className="text-[11px] text-muted">fundamental analysis</div>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {LINKS.map((l) => {
          const active = pathname === l.href || (l.href !== "/" && pathname.startsWith(l.href));
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`block rounded px-3 py-2 text-sm transition-colors ${
                active ? "bg-panel2 text-ink" : "text-muted hover:bg-panel2/60 hover:text-ink"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-line p-3">
        <div className="truncate text-[11px] text-muted">{email}</div>
        <button onClick={logout} className="mt-1 text-[11px] text-steel hover:text-ink">
          Sign out
        </button>
      </div>
    </aside>
  );
}
