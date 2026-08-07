"""Command-line entrypoints (no server needed).

    uv run python -m app.cli generate [YYYY-MM-DD]
        Run the full pipeline and persist an edition.

    uv run python -m app.cli discover [--scrape] [--web-only] [--json PATH]
        Run ONLY discovery (+ optional scraping) and print what the research
        agent found — to inspect relevance/veracity of the collected data.

    uv run python -m app.cli cleanup [--days N]
        Purge editions older than the retention window (RETENTION_DAYS).
"""

from __future__ import annotations

import argparse
import json

from sqlmodel import Session

from datetime import datetime, timezone

from .db import engine, init_db
from .pipeline import discovery, relevance, scraper
from .pipeline.llm import get_llm
from .pipeline.orchestrator import purge_old_editions, run_pipeline


def _cmd_generate(args: argparse.Namespace) -> None:
    init_db()
    with Session(engine) as session:
        edition = run_pipeline(session, args.date)
        print(
            f"\n✓ Edition {edition.date} — '{edition.title}' "
            f"({len(edition.articles)} articles, model={edition.model})"
        )
        for a in edition.articles:
            print(f"  [{a.rank}] {a.category:<9} ★{a.importance} {a.headline[:70]}")


def _cmd_discover(args: argparse.Namespace) -> None:
    candidates = discovery.discover_candidates()
    if args.web_only:
        candidates = [c for c in candidates if c.origin == "web"]

    # Relevance agent (optional) — score every candidate, keep all for display.
    verdicts = {}
    if args.filter:
        llm = get_llm()
        scored = relevance.score_candidates(llm, candidates)
        verdicts = {id(sc.candidate): sc for sc in scored}

    if args.scrape:
        scraper.enrich(candidates)

    n_rss = sum(1 for c in candidates if c.origin == "rss")
    n_web = sum(1 for c in candidates if c.origin == "web")
    n_content = sum(1 for c in candidates if c.has_content)
    n_keep = sum(1 for sc in verdicts.values() if sc.keep)

    print("\n" + "=" * 78)
    print(
        f"DISCOVERY: {len(candidates)} candidates  "
        f"(rss={n_rss}, web={n_web}"
        + (f", with_extracted_text={n_content}" if args.scrape else "")
        + (f", KEEP={n_keep}/{len(candidates)}" if args.filter else "")
        + ")"
    )
    print("=" * 78)

    for i, c in enumerate(candidates):
        pub = c.published.strftime("%Y-%m-%d %H:%M") if c.published else "     no date    "
        tag = "WEB" if c.origin == "web" else "rss"
        flag = ""
        if args.scrape:
            flag = f" | text:{len(c.content):>5}c" if c.has_content else " | text:  NONE"
        verdict = ""
        if args.filter and id(c) in verdicts:
            sc = verdicts[id(c)]
            verdict = f" | {'KEEP' if sc.keep else 'DROP'} {sc.score:>3}"
        print(f"\n[{i:>2}] ({tag}) {pub} · {c.publisher}{flag}{verdict}")
        print(f"     {c.title}")
        print(f"     {c.url}")
        if args.filter and id(c) in verdicts:
            print(f"     ⚖  {verdicts[id(c)].reason}")
        elif c.snippet:
            print(f"     ↳ {c.snippet[:160]}")

    if args.json:
        payload = [c.model_dump(mode="json") for c in candidates]
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"\n→ Full data written to {args.json}")


def _cmd_cleanup(args: argparse.Namespace) -> None:
    from .config import settings

    init_db()
    today = datetime.now(timezone.utc).date().isoformat()
    days = settings.retention_days if args.days is None else args.days
    with Session(engine) as session:
        n = purge_old_editions(session, today, days=args.days)
    if days <= 0:
        print("Retention disabled (days <= 0) — nothing purged.")
    else:
        print(f"✓ Purged {n} edition(s) older than {days} days.")


def _cmd_models(args: argparse.Namespace) -> None:
    """List the Gemini models the configured API key can actually use."""
    from .config import settings

    if not settings.gemini_api_key:
        print("No GEMINI_API_KEY set — cannot list models.")
        raise SystemExit(1)

    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    print("Configured fallback chain :", ", ".join(settings.gemini_model_list))
    print("\nModels available to this key (supporting generateContent):\n")
    available: list[str] = []
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or getattr(
            m, "supported_generation_methods", []
        )
        if actions and "generateContent" not in actions:
            continue
        name = m.name.split("/")[-1]
        available.append(name)
        print(f"  {name}")

    missing = [m for m in settings.gemini_model_list if m not in available]
    if missing:
        print("\n⚠  In your chain but NOT available:", ", ".join(missing))
        print("   Update GEMINI_MODELS with the exact IDs listed above.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Run the full pipeline and persist an edition.")
    p_gen.add_argument("date", nargs="?", default=None, help="Edition date YYYY-MM-DD (default: today).")
    p_gen.set_defaults(func=_cmd_generate)

    p_disc = sub.add_parser("discover", help="Inspect what discovery/web-search returns.")
    p_disc.add_argument("--scrape", action="store_true", help="Also fetch & extract article text.")
    p_disc.add_argument("--web-only", action="store_true", help="Show only web-search results.")
    p_disc.add_argument(
        "--filter", action="store_true", help="Run the relevance agent and show KEEP/DROP + score."
    )
    p_disc.add_argument("--json", metavar="PATH", help="Also dump full candidate data as JSON.")
    p_disc.set_defaults(func=_cmd_discover)

    p_clean = sub.add_parser("cleanup", help="Purge editions older than the retention window.")
    p_clean.add_argument(
        "--days", type=int, default=None, help="Override RETENTION_DAYS (0 = disabled)."
    )
    p_clean.set_defaults(func=_cmd_cleanup)

    p_models = sub.add_parser("models", help="List Gemini models available to your API key.")
    p_models.set_defaults(func=_cmd_models)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
