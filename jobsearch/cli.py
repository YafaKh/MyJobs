"""Command-line entrypoint.

Usage:
    python -m jobsearch.cli show-config
    python -m jobsearch.cli init-db
    python -m jobsearch.cli add-source --name "Stripe" --url "https://boards.greenhouse.io/stripe"
    python -m jobsearch.cli seed-feeds
    python -m jobsearch.cli list-sources
    python -m jobsearch.cli fetch
    python -m jobsearch.cli extract
    python -m jobsearch.cli quota
    python -m jobsearch.cli cleanup
    python -m jobsearch.cli serve
"""

import argparse
import json
from datetime import date

import httpx

from jobsearch import quota as quota_module
from jobsearch.agent import run as agent_run
from jobsearch.ats.detect import detect_ats
from jobsearch.cleanup import cleanup_unstarred
from jobsearch.config import load_config
from jobsearch.db import connect, init_db
from jobsearch.env import load_env
from jobsearch.feeds import FEEDS
from jobsearch.fetch import run as fetch_run


def cmd_show_config(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    print(json.dumps(config, indent=2))


def cmd_init_db(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    db_path = args.db or config["storage"]["db_path"]
    init_db(db_path)
    print(f"Initialized SQLite schema at {db_path}")


def cmd_add_source(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    conn = connect(config["storage"]["db_path"])
    client = httpx.Client(headers={"User-Agent": config["scraping"]["user_agent"]}, follow_redirects=True)
    try:
        ats_type, identifier = detect_ats(args.url, client)
    finally:
        client.close()

    conn.execute(
        "INSERT INTO sources (name, careers_url, ats_type, ats_identifier) VALUES (?, ?, ?, ?)",
        (args.name, args.url, ats_type, identifier),
    )
    conn.commit()
    conn.close()
    print(f"Added '{args.name}' -> detected ATS: {ats_type} (identifier: {identifier})")


def cmd_seed_feeds(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    conn = connect(config["storage"]["db_path"])
    added = 0
    for feed in FEEDS:
        existing = conn.execute("SELECT id FROM sources WHERE name = ?", (feed["name"],)).fetchone()
        if existing:
            continue
        conn.execute(
            "INSERT INTO sources (name, careers_url, source_kind, ats_type) VALUES (?, ?, 'openweb', ?)",
            (feed["name"], feed["url"], feed["key"]),
        )
        added += 1
    conn.commit()
    conn.close()
    print(f"Added {added} new open web feed(s) ({len(FEEDS) - added} already present)")


def cmd_list_sources(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    conn = connect(config["storage"]["db_path"])
    rows = conn.execute("SELECT * FROM sources ORDER BY id").fetchall()
    conn.close()

    if not rows:
        print("No sources yet. Add one with add-source.")
        return

    for r in rows:
        status = "active" if r["is_active"] else "inactive"
        health = "healthy" if r["consecutive_failures"] == 0 else f"UNHEALTHY ({r['consecutive_failures']} failures)"
        print(f"[{r['id']}] {r['name']} - {r['ats_type'] or 'undetected'} - {status} - {health}")
        if r["last_success_at"]:
            print(f"    last success: {r['last_success_at']}")
        if r["last_error"]:
            print(f"    last error ({r['last_checked_at']}): {r['last_error']}")


def cmd_fetch(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    conn = connect(config["storage"]["db_path"])
    try:
        fetch_run(conn, config["scraping"])
    finally:
        conn.close()


def cmd_extract(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    conn = connect(config["storage"]["db_path"])
    try:
        agent_run(conn, config)
    finally:
        conn.close()


def cmd_quota(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    conn = connect(config["storage"]["db_path"])
    today = date.today().isoformat()
    used = quota_module.get_today_usage(conn, today)
    conn.close()
    print(f"{used}/{config['llm']['daily_quota_cap']} LLM calls used today ({today})")


def cmd_cleanup(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    conn = connect(config["storage"]["db_path"])
    deleted = cleanup_unstarred(conn, config["storage"]["job_retention_days"])
    conn.close()
    print(f"Deleted {deleted} unstarred job(s) older than {config['storage']['job_retention_days']} days")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("jobsearch.web.app:app", host=args.host, port=args.port, reload=args.reload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobsearch", description="Personal job search tool")
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config.yaml (default: config.yaml)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_config = subparsers.add_parser("show-config", help="Load config.yaml and print it")
    show_config.set_defaults(func=cmd_show_config)

    init_db_cmd = subparsers.add_parser("init-db", help="Create the SQLite schema")
    init_db_cmd.add_argument(
        "--db", default=None, help="Override storage.db_path from config.yaml"
    )
    init_db_cmd.set_defaults(func=cmd_init_db)

    add_source_cmd = subparsers.add_parser("add-source", help="Add a saved company source")
    add_source_cmd.add_argument("--name", required=True, help="Company name")
    add_source_cmd.add_argument("--url", required=True, help="Careers page URL")
    add_source_cmd.set_defaults(func=cmd_add_source)

    seed_feeds_cmd = subparsers.add_parser("seed-feeds", help="Register the fixed open web feeds as sources")
    seed_feeds_cmd.set_defaults(func=cmd_seed_feeds)

    list_sources_cmd = subparsers.add_parser("list-sources", help="List all sources and their health")
    list_sources_cmd.set_defaults(func=cmd_list_sources)

    fetch_cmd = subparsers.add_parser("fetch", help="Fetch jobs for all active sources (saved + open web)")
    fetch_cmd.set_defaults(func=cmd_fetch)

    extract_cmd = subparsers.add_parser("extract", help="Run LLM extraction on unextracted jobs")
    extract_cmd.set_defaults(func=cmd_extract)

    quota_cmd = subparsers.add_parser("quota", help="Show today's LLM call usage")
    quota_cmd.set_defaults(func=cmd_quota)

    cleanup_cmd = subparsers.add_parser("cleanup", help="Delete unstarred jobs older than the retention window")
    cleanup_cmd.set_defaults(func=cmd_cleanup)

    serve_cmd = subparsers.add_parser("serve", help="Run the dashboard web server")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8000)
    serve_cmd.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev only)")
    serve_cmd.set_defaults(func=cmd_serve)

    return parser


def main() -> None:
    load_env()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
