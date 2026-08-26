"""Command-line entrypoint.

Usage:
    python -m jobsearch.cli show-config
    python -m jobsearch.cli init-db
"""

import argparse
import json

from jobsearch.config import load_config
from jobsearch.db import init_db


def cmd_show_config(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    print(json.dumps(config, indent=2))


def cmd_init_db(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    db_path = args.db or config["storage"]["db_path"]
    init_db(db_path)
    print(f"Initialized SQLite schema at {db_path}")


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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
