export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("ft_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...authHeaders(), ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; email: string; is_admin: boolean }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  currencies: () => request<CurrencyScore[]>("/api/currencies"),
  currency: (ccy: string) => request<CurrencyScore>(`/api/currencies/${ccy}`),
  explainCurrency: (ccy: string) => request<Explain>(`/api/currencies/${ccy}/explain`),
  pair: (pair: string) => request<Pair>(`/api/pairs/${pair.replace("/", "-")}`),
  explainPair: (pair: string) => request<PairExplain>(`/api/pairs/${pair.replace("/", "-")}/explain`),
  pairsList: () => request<string[]>("/api/pairs"),
  news: (currency?: string, hours = 72) =>
    request<NewsItem[]>(`/api/news?${currency ? `currency=${currency}&` : ""}hours=${hours}`),
  calendar: (currency?: string) => request<CalEvent[]>(`/api/calendar${currency ? `?currency=${currency}` : ""}`),
  centralBanks: () => request<CentralBank[]>("/api/central-banks"),
  status: () => request<Status>("/api/status"),
};

export type Factor = { factor: string; label: string; score: number | null; notes: string; stale: boolean };
export type CurrencyScore = {
  currency: string;
  total: number | null;
  coverage: number;
  confidence: string;
  surprise_method: string;
  computed_at: string | null;
  factors: Factor[];
};
export type Explain = { text: string; origin: string; drivers: string[] };
export type PairExplain = { text: string; origin: string; differential: number | null };
export type Pair = {
  pair: string;
  base: string;
  quote: string;
  price: { pair: string; mid: number; ts: string; source: string; is_reference: boolean } | null;
  base_score: CurrencyScore;
  quote_score: CurrencyScore;
  differential: number | null;
};
export type NewsItem = {
  id: number;
  currency: string;
  headline: string;
  summary: string | null;
  published_at: string;
  source: string;
  source_url: string;
  category: string;
  tone: number;
  impact: string;
};
export type CalEvent = {
  id: number;
  currency: string;
  title: string;
  event_date: string;
  event_time: string | null;
  impact: string;
  kind: string;
  actual: string | null;
  forecast: string | null;
  previous: string | null;
  source: string;
  source_url: string | null;
};
export type CentralBank = {
  currency: string;
  bank: string;
  stance: string | null;
  policy_rate: number | null;
  rate_effective_date: string | null;
  next_meeting: string | null;
  statement_url: string | null;
  notes: string | null;
};
export type Status = {
  demo_mode: boolean;
  jobs: { name: string; last_run: string | null; status: string | null; error: string | null; detail: string | null }[];
  providers: Record<string, string[]>;
  quota: Record<string, { used_today: number }>;
};
