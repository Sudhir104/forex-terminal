# Forex Fundamental Terminal

A private currency-strength and fundamental-analysis dashboard for you and a few friends.
Free-tier-first: every data source has a free implementation, and every provider is
swappable for a paid one through config alone — no rewrite.

```
External APIs (free or paid, same interface either way)
        |
Provider chain (fallback + circuit breaker + daily-quota guard)
        |
PostgreSQL (raw + normalised, every row keeps source + timestamp)
        |
Currency Strength Engine  (8 weighted factors, explainable, degrades gracefully)
        |
FastAPI  --->  Next.js dashboard  --->  you + friends
```

## What's in here

```
backend/
  app/
    providers/      one file per data source (fx_twelvedata, macro_fred, news_rss, ...),
                     each implementing a small interface in providers/base.py
    services/        ingest.py (orchestrator), scoring.py (the engine), explain.py (AI layer),
                     repo.py (DB upserts), auth.py, alerts.py, crosses.py, weights.py
    api/             FastAPI routers (currencies, pairs, news, calendar, central-banks, admin)
    models.py        SQLAlchemy tables
    cli.py            python -m app.cli <command> — see below
  data/
    feeds.yaml         RSS feeds for the free news provider
    central_banks.yaml the one thing worth curating by hand: policy stance + meeting dates
  tests/               35 unit + API tests, run with `pytest`
frontend/
  src/app/             Next.js pages: overview, currency detail, pair analyzer, calendar, news, central banks
  src/components/       ScoreBadge, FactorBars, NewsRow, EventRow, Sidebar, Panel
  src/lib/               typed API client + auth context (JWT in localStorage)
render.yaml            Render blueprint (backend + free Postgres)
frontend/vercel.json    Vercel config (frontend)
.github/workflows/      cron.yml — keeps ingestion running even while Render's free web
                        service is asleep, by hitting /api/internal/tick/{job}
docker-compose.yml      local Postgres + backend for development
```

## Try it in 2 minutes (no API keys)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DEMO_MODE=true ENABLE_SCHEDULER=false
python -m app.cli create-user you@example.com yourpassword   # first user becomes admin
python -m app.cli seed-demo                                   # one full ingest+score pass, synthetic data
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000, sign in, and you'll see the full dashboard running on made-up
numbers (every demo value is tagged `is_demo`/`[DEMO]` at the source). This is the fastest
way to check the UI and API without any accounts.

## Going live on free data

1. Get two free keys (no credit card):
   - **Twelve Data** — https://twelvedata.com/pricing → free Basic plan → live FX prices
   - **FRED** — https://fred.stlouisfed.org/docs/api/api_key.html → US economic data + VIX
2. Put them in `backend/.env` (`TWELVEDATA_API_KEY`, `FRED_API_KEY`), set `DEMO_MODE=false`.
3. `python -m app.cli doctor` — checks your keys and RSS feed health in one shot.
4. `python -m app.cli tick fx` / `tick macro-full` / `tick news` / `tick calendar` / `tick scores`
   to run each collector once and watch it populate the database.
5. Fill in `data/central_banks.yaml` by hand from the linked official pages — it's the one
   part of the model that's genuinely worth a human's judgement (8 banks, ~8 meetings/year each).

EUR, GBP, JPY, CHF, AUD, NZD and CAD macro data come free from the ECB, Bank of Canada and
Bank of England APIs plus FRED's OECD-mirrored series (no key beyond FRED's). Coverage is
uneven on the free tier by design — the `coverage` and `confidence` fields on every score
tell you honestly how much data backs a number, rather than silently padding it.

## Free-tier engineering that keeps this honest

- **Fetch 7, derive 28**: only the 7 USD pairs hit the FX API; the other 21 crosses are
  computed locally (`services/crosses.py`), cutting API credits ~4x.
- **Quota-aware polling**: `providers/resilience.py` tracks daily credit usage and stretches
  the polling interval automatically so a free plan's budget lasts until midnight UTC instead
  of running out by lunchtime.
- **Circuit breaker + fallback chain**: a failing provider opens its breaker (exponential
  backoff) and the next provider in the chain takes over — one dead source never blocks
  ingestion, and every fallback is visible at `GET /api/status`.
- **Fact / calculation / interpretation kept separate**: raw provider data → `scoring.py`'s
  deterministic factor math → an optional AI sentence in `explain.py` that is only ever
  asked to phrase numbers it's given, never to invent one.
- **`forecast` is nullable everywhere**: the free tier has no consensus data, so "surprise"
  degrades to actual-vs-previous and says so (`surprise_method` on every score) instead of
  faking a number. Add a paid calendar provider later and it upgrades itself automatically.

## Moving a data type to paid, later

Nothing else in the codebase needs to change. Example — adding real consensus forecasts:

```bash
# backend/.env
CALENDAR_PROVIDERS=tradingeconomics,official   # paid primary, free fallback
TRADINGECONOMICS_API_KEY=...
```

`providers/calendar_tradingeconomics.py` already implements the same `CalendarProvider`
interface as the free one, normalises into the same `EventObs`, and lands in the same
`calendar_events` table. `scoring.py`, the API and the UI don't know or care which provider
ran. The same pattern applies to `FX_PROVIDERS`, `MACRO_PROVIDERS` and `NEWS_PROVIDERS`.
Check each paid provider's terms before showing its data to friends — some plans restrict
redistribution to a "personal use" login, which this dashboard's private auth satisfies, but
read the terms yourself before relying on that.

## Deploying (free)

- **Backend → Render**: connect the repo, "New +" → "Blueprint" → picks up `render.yaml`
  (free web service + free Postgres). Add `TWELVEDATA_API_KEY` / `FRED_API_KEY` in the
  dashboard (marked `sync: false` so they're not committed). Free Render services sleep
  after 15 idle minutes — `ENABLE_SCHEDULER=false` plus `.github/workflows/cron.yml` keeps
  data flowing anyway by hitting the service on a schedule (which also keeps it warm).
- **Frontend → Vercel**: import the repo, set root directory to `frontend`, add
  `NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com`.
- **Database**: Render's free Postgres expires after 30 days of inactivity — if that bites
  you, swap in Supabase or Neon's free tier instead (just change `DATABASE_URL`; nothing
  else changes).
- No domain needed — `*.vercel.app` and `*.onrender.com` are enough for a private group.

## Accounts

There's no public sign-up route on purpose. Create logins with:

```bash
python -m app.cli create-user friend@example.com theirpassword
```

The first account created becomes admin automatically (can retune scoring weights via
`PUT /api/admin/weights`, create more users, and reload central-bank data).

## AI explanation layer (optional)

`LLM_PROVIDER=none` by default — every score already has a template explanation built
straight from its evidence, so the dashboard works with zero AI cost. Set
`LLM_PROVIDER=anthropic` (or `groq`) with the matching API key to have that same evidence
phrased as a sentence by a real model instead. It is prompted to explain, never to invent —
see the system prompt in `services/explain.py` — and every explanation is cached by a hash
of its input facts so an unchanged score never re-spends a token.

## Tests

```bash
cd backend && source .venv/bin/activate && pytest
```

35 tests: scoring math (rate hikes/cuts, inverted indicators, missing-factor handling, yield
spreads, surprise-vs-forecast-vs-previous), cross-rate derivation, the quota/circuit-breaker
resilience layer, RSS/Atom parsing across real-world feed shapes, FRED series transforms, and
FastAPI integration tests (auth, 401/403/404 handling, admin-only routes).
