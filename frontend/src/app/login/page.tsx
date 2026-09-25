"use client";
import { useState, FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, email } = useAuth();
  const [emailInput, setEmailInput] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (email) return null;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(emailInput, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-md border border-line bg-panel p-6">
        <div className="mb-6">
          <div className="font-mono text-lg font-bold tracking-tight text-gold">FX TERMINAL</div>
          <p className="mt-1 text-sm text-muted">Sign in to your private dashboard</p>
        </div>
        <label className="mb-3 block">
          <span className="mb-1 block text-xs text-muted">Email</span>
          <input
            type="email"
            required
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            className="w-full rounded border border-line bg-panel2 px-3 py-2 text-sm text-ink outline-none focus:border-gold"
          />
        </label>
        <label className="mb-4 block">
          <span className="mb-1 block text-xs text-muted">Password</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-line bg-panel2 px-3 py-2 text-sm text-ink outline-none focus:border-gold"
          />
        </label>
        {error && <p className="mb-4 text-xs text-neg">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-gold px-3 py-2 text-sm font-medium text-bg transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="mt-4 text-[11px] text-muted">
          No public sign-up — ask whoever runs the terminal to create your account with{" "}
          <code className="font-mono">python -m app.cli create-user</code>.
        </p>
      </form>
    </div>
  );
}
