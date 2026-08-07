# 📰 The Daily Model — AI News

[![CI](https://github.com/mjebalidev/thedailymodel/actions/workflows/ci.yml/badge.svg)](https://github.com/mjebalidev/thedailymodel/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An automated **daily newspaper about AI**. A research agent discovers fresh AI
news, an LLM analyzes and clusters it, then writes a journalistic edition that is
served through a classic newspaper-style web UI.

```
 trigger ─▶ discover ─▶ relevance ─▶ scrape ─▶ analysis ─▶ editorial ─▶ translate ─▶ display
 (cron/CI)  (RSS + web) (agent drops (extract) (select/    (LLM        (agent →      (React
                         noise)                 cluster)    writes)      fr, de)       gazette)
```

## Stack

| Layer        | Tech                                                              |
| ------------ | ---------------------------------------------------------------- |
| Backend      | **Python + FastAPI** (managed with **uv**), SQLModel + SQLite     |
| LLM          | **Gemini** free tier (`google-genai`) with an ordered **model fallback chain**; swappable, with mock mode |
| Discovery    | **RSS feeds** (labs, media, arXiv) + **DuckDuckGo** (`ddgs`, no key) |
| Scraping     | **trafilatura** (browser-free article extraction)                 |
| Agents       | Relevance (noise filter) · Editorial (writing) · Translation (fr/de) |
| Languages    | **EN base + FR/DE** translated by agent; UI + content localized   |
| Scheduling   | CI (schedule + manual dispatch) → secret-guarded trigger endpoint |
| Frontend     | **React + TS + Vite + Tailwind v4** — gazette theme, light/dark/sepia |

Everything runs **with zero API keys** out of the box thanks to a deterministic
*mock* mode — you get real discovery + scraping and a rendered edition immediately.
Add a Gemini key when you want real analysis and writing.

## Quick start

```bash
# 1. Install everything
make install                 # or: cd backend && uv sync ; cd frontend && npm install

# 2. Configure the backend
cp backend/.env.example backend/.env   # works as-is in mock mode

# 3. Run it (two terminals)
make backend                 # API  -> http://127.0.0.1:8000  (docs at /docs)
make frontend                # UI   -> http://127.0.0.1:5173
```

The site is **read-only**: editions are produced by the pipeline, not by visitors.
To build one locally, run `make generate` (the CLI runs the pipeline directly, no
server needed). In production, generation is triggered by CI — see **Deployment**.

## Enabling real AI (Gemini free tier)

1. Grab a free key at https://aistudio.google.com/apikey
2. In `backend/.env`:
   ```env
   GEMINI_API_KEY=your_key_here
   USE_MOCK_LLM=false
   ```
3. Restart the backend. `GET /api/health` reports `"llm": "gemini"` and the model chain.

**Model fallback chain.** `GEMINI_MODELS` is an ordered list (smartest → most
available), default `gemini-3-flash,gemini-3.5-flash,gemini-2.5-flash,gemini-2.5-flash-lite`.
Each call tries them in order: a model that's missing / access-denied is skipped
permanently; transient errors (rate limit, 5xx) are retried, then the next model
is tried. If every model fails, the pipeline **falls back to the deterministic
mock** so an edition is always produced. `Edition.model` records what actually ran.

> The exact v3 IDs vary by account — verify what your key can use:
> ```bash
> uv run python -m app.cli models
> ```
> then set `GEMINI_MODELS` to the exact IDs it lists.

## How the workflow is wired

| Step        | File                                  | What it does |
| ----------- | ------------------------------------- | ------------ |
| Trigger     | `app/api/pipeline.py`, `app/runner.py`| Manual `POST /api/pipeline/trigger` or the daily cron; runs async in a thread, progress via `/api/pipeline/status`. |
| Discovery   | `app/pipeline/discovery.py` + `sources.py` | Pulls RSS feeds and DuckDuckGo news, dedupes, filters to `LOOKBACK_HOURS`, distrusts future dates. |
| Relevance   | `app/pipeline/relevance.py`           | Agent scores each candidate for AI-news relevance and drops the noise (heuristic in mock). |
| Scraping    | `app/pipeline/scraper.py`             | Fetches each *relevant* URL and extracts clean article text with trafilatura. |
| Analysis    | `app/pipeline/analysis.py`            | LLM selects / clusters / categorizes / ranks stories (heuristic in mock). |
| Editorial   | `app/pipeline/editorial.py`           | LLM writes the masthead intro + each article body (templated in mock). |
| Translation | `app/pipeline/translation.py`         | Agent translates the edition into the non-base languages (no-op in mock). |
| Persist     | `app/pipeline/orchestrator.py`        | Saves one `Edition` (+ `Article`s, + i18n) per day, idempotently; then purges editions older than `RETENTION_DAYS`. |
| Display     | `frontend/src/`                       | Fetches `/api/editions/*?lang=` and renders the newspaper. |

## Triggering the pipeline

The pipeline is **not** exposed to site visitors. There are three ways to run it:

| Context      | How |
| ------------ | --- |
| **Local**    | `make generate` — runs the pipeline via the CLI, writes to the DB. |
| **Production (scheduled + manual)** | **CI** (`.github/workflows/daily-edition.yml`): a daily `schedule` **and** a manual `workflow_dispatch` button, both calling `POST /api/pipeline/trigger` with the `X-Trigger-Secret` header. |
| **Ops / debug** | Coolify container **Terminal** → `uv run python -m app.cli generate`. |

The HTTP endpoint is guarded by `TRIGGER_SECRET` (constant-time check). Leave it
empty locally to keep the endpoint open; **set it in production** so only CI can trigger.

## Inspecting & verifying the data

**Final edition (what's published)** — every article stores and displays its
**sources** (title + URL + publisher). Click them in the UI, or read them from
`GET /api/editions/{date}`, to check each claim against the original article.

**Discovery / web-search relevance (upstream)** — inspect what the research agent
actually finds, tagged by origin (`rss` vs `web`), without writing anything:

```bash
# What did discovery return? (RSS + DuckDuckGo, tagged by origin)
uv run python -m app.cli discover

# Only the web-search hits — to judge their relevance
uv run python -m app.cli discover --web-only

# Run the relevance agent and see what it KEEPs / DROPs, with score + reason
uv run python -m app.cli discover --filter

# Also fetch & extract article text (shows how many chars trafilatura got)
uv run python -m app.cli discover --scrape

# Dump everything to JSON for deeper review
uv run python -m app.cli discover --json /tmp/discovery.json
```

In production, run the same command from the **Coolify container Terminal**. The
`--scrape` flag is the quickest way to spot pages where extraction failed
(`text: NONE`) — those articles reach the LLM with only their RSS/search snippet.

> Tip: web-search dates can be unreliable (some feeds report future/incorrect
> `published` values), which can push a loosely-related item to the top. `discover`
> makes these easy to spot before they influence an edition.

## Languages (i18n)

The paper is multilingual. **English is the base** language (the edition is written
in it); a **translation agent** renders each edition into the other languages,
stored alongside the original.

- Configure with `LANGUAGES` (ISO 639-1, first = base), default `en,fr,de`.
- The API serves any language via `?lang=`, e.g. `GET /api/editions/latest?lang=fr`
  (falls back to the base text where a translation is missing). `available_languages`
  in the response lists what that edition actually has.
- The frontend has a **EN / FR / DE switcher** in the masthead (persisted); it
  localizes both the UI chrome (`src/i18n.tsx`) and the article content (via the API).
- In mock mode translation is a no-op — only the base language is produced.

Add a language: append its code to `LANGUAGES`, add its labels to the `DICT` /
`CATEGORY` maps in `frontend/src/i18n.tsx`, and add it to `LANGS`.

## Reading experience

The frontend is a classic gazette: Playfair Display nameplate, Source Serif body,
justified columns with column rules, a lead story with a drop cap, and a category
section filter. It ships **light / dark ("Evening Edition") / sepia ("Newsprint")**
themes (toggle in the masthead, remembers your choice, respects `prefers-color-scheme`),
a condensing sticky masthead, and is tuned for phones (fluid nameplate, 44px tap
targets, overflow-safe). All motion respects `prefers-reduced-motion`.

## Extending it

The pipeline is intentionally provider-agnostic:

- **Swap the LLM** — implement the same `generate_structured(prompt, schema)`
  interface as `GeminiLLM` in `app/pipeline/llm.py` (e.g. Anthropic, OpenAI, a
  local model) and return it from `get_llm()`.
- **Better search** — add **Tavily/Exa** in `discovery.py`, or self-host
  **SearXNG** as a metasearch source.
- **Heavier scraping** — swap trafilatura for **Crawl4AI** (Playwright, JS-rendered
  pages → LLM-ready markdown) in `scraper.py`.
- **Tune coverage** — `LOOKBACK_HOURS`, `MAX_CANDIDATES`, `MAX_ARTICLES` in `.env`.
- **Add/remove sources** — edit `RSS_FEEDS` in `app/pipeline/sources.py`.
- **Bound the archive** — `RETENTION_DAYS` (default 365, `0` = keep everything):
  editions older than the window are purged after each run. Manual purge:
  `uv run python -m app.cli cleanup [--days N]`.

## Development & CI

```bash
make lint   # ruff over the backend
make test   # pytest suite (backend/tests/)
```

The test suite covers the retention purge, the editions API (ordering, counts,
i18n fallback), the LLM fallback-chain semantics (dead-model skip, transient
retry, exhaustion), trigger authentication and error sanitization — all against
a throwaway SQLite database, no network or API key needed.

CI (`.github/workflows/ci.yml`) runs ruff + pytest and type-checks/builds the
frontend on every push and PR; **Renovate** keeps dependencies current.

## Deployment (Vercel + Coolify/Hetzner)

Frontend → **Vercel** (free tier), backend → **Coolify** on a **Hetzner VPS**.
Both auto-deploy on `git push`.

```mermaid
flowchart TB
    subgraph CI["⏰ CI — GitHub / Forgejo Actions (daily cron 04:00 UTC)"]
        cron["daily-edition.yml
POST /api/pipeline/trigger
header X-Trigger-Secret"]
    end

    subgraph BACK["🐍 Backend — FastAPI + uv · Docker on Coolify (Hetzner VPS)"]
        api["REST API
/api/pipeline · /api/editions"]
        subgraph PIPE["Daily pipeline (idempotent per date)"]
            d["1 · Discovery
RSS feeds + DuckDuckGo search
48 h window, max 40 candidates"]
            r["2 · Relevance agent
score 0–100, drop &lt; 50"]
            s["3 · Scraper
full text (best-effort)"]
            a["4 · Analysis agent
category · importance · summary"]
            e["5 · Editorial agent
title + intro, max 12 articles"]
            t["6 · Translation agent
EN → FR / DE"]
            ret["7 · Retention
purge editions &gt; RETENTION_DAYS"]
        end
        db[("SQLite — /data volume
editions · articles · i18n_json")]
    end

    subgraph LLM["✨ LLM — Gemini free tier"]
        chain["Fallback chain
gemini-flash-latest → gemini-flash-lite-latest
→ deterministic mock if all fail"]
    end

    subgraph FRONT["⚛️ Frontend — React + TypeScript + Vite · Vercel"]
        spa["Static SPA (read-only)
EN/FR/DE · themes · archive"]
    end

    cron -- "secured trigger + /status polling" --> api
    api --> d --> r --> s --> a --> e --> t --> ret
    t -- "persist (replaces the day's edition)" --> db
    ret -- "delete old editions + articles" --> db
    r -.-> chain
    a -.-> chain
    e -.-> chain
    t -.-> chain
    spa -- "GET /api/editions (CORS)" --> api
    db --> api
```

### Frontend on Vercel

1. New Project → import the repo.
2. **Root Directory = `frontend`** (Vercel reads `frontend/vercel.json`, preset = Vite).
3. Env var → `VITE_API_BASE_URL = https://api.example.com` (your Coolify URL, no trailing slash).
4. Deploy. Every push to the repo redeploys automatically.

### Backend on Coolify (Hetzner)

1. New Resource → **Dockerfile** from the repo, **Base Directory = `/backend`**.
2. Exposed port: **8000**.
3. **Persistent storage** — mount a volume at **`/data`** so the SQLite DB survives
   redeploys (the Dockerfile already sets `DATABASE_URL=sqlite:////data/ai_news.db`).
   The container runs as a **non-root user (uid 1000)**: a named/managed volume
   inherits the right ownership from the image, but if you bind-mount a host
   directory, `chown -R 1000` it first.
4. Environment variables:
   ```env
   USE_MOCK_LLM=false
   GEMINI_API_KEY=your_key
   CORS_ORIGINS=https://example.com
   TRIGGER_SECRET=some-long-secret
   # DATABASE_URL is already set to the volume path by the Dockerfile.
   ```
5. Enable auto-deploy (Coolify GitHub app / webhook) → push rebuilds the container.

> Prefer Postgres over SQLite? Add a Postgres service in Coolify and set
> `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db` (add the `psycopg`
> dependency). No code change needed — SQLModel handles both.

### Triggering in production (CI)

Generation is driven by `.github/workflows/daily-edition.yml` (works on GitHub
Actions and Forgejo/Gitea Actions):

- **Scheduled** — daily `cron` (default 04:00 UTC).
- **Manual** — the **Run workflow** button (`workflow_dispatch`), with an optional date.

Add two secrets to the repo (Settings → Secrets and variables → Actions):

| Secret           | Value |
| ---------------- | ----- |
| `API_BASE_URL`   | `https://api.example.com` (no trailing slash) |
| `TRIGGER_SECRET` | the same value set in the backend env on Coolify |

The workflow POSTs the trigger, then polls `/api/pipeline/status` until the run
reports `done` (fails the job on `error`/timeout).

> On **GitLab**, use a scheduled pipeline + a manual job in `.gitlab-ci.yml` with the
> same `curl` call.

## API

| Method | Path                          | Description                    |
| ------ | ----------------------------- | ------------------------------ |
| GET    | `/api/health`                 | Status, LLM model chain, languages |
| GET    | `/api/editions?lang=`         | List all editions (summaries)  |
| GET    | `/api/editions/latest?lang=`  | Latest full edition            |
| GET    | `/api/editions/{YYYY-MM-DD}?lang=` | A specific edition (lang: en/fr/de) |
| POST   | `/api/pipeline/trigger`       | Start a generation run (`X-Trigger-Secret` header) |
| GET    | `/api/pipeline/status`        | Progress of the current run    |
