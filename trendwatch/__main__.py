"""TrendWatch CLI.

Usage:
    python -m trendwatch run      # check trends and send alerts (what CI runs)
    python -m trendwatch quota    # estimate monthly API usage for your config
    python -m trendwatch test     # send a test alert to every configured channel
    python -m trendwatch check    # validate config.yml + API key, no alerts
"""
from __future__ import annotations

import argparse
import sys

# Make emoji/checkmarks safe on consoles that default to a legacy codepage
# (e.g. Windows cp1252). GitHub Actions runners are already UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from . import __version__
from .client import MissingKey, RateLimited, TrendsClient, TrendsError
from .config import load_config
from .monitor import run_monitor
from .notifiers import configured_channels, dispatch, send_test
from .quota import print_report
from .report import build_markdown, update_readme, write_reports
from .state import load_state, save_state


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    client = TrendsClient()
    state = load_state()

    print(f"TrendWatch v{__version__}")
    active = configured_channels()
    print(f"Channels: {', '.join(active) if active else 'console only (add a webhook secret to get notified)'}")

    events, leaderboards = run_monitor(client, cfg, state)
    print(f"\nDetected {len(events)} event(s); used ~{client.calls_made} API request(s) this run.")

    dispatch(events)

    if cfg.write_markdown or cfg.update_readme:
        markdown = build_markdown(events, leaderboards)
        if cfg.write_markdown:
            write_reports(markdown)
        if cfg.update_readme:
            update_readme(events, leaderboards)

    save_state(state)
    print("Done.")
    return 0


def cmd_quota(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    print_report(cfg)
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    send_test()
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    print(f"✓ config.yml parsed: {len(cfg.watchlist)} keyword(s), {len(cfg.discovery_feeds)} feed(s)")
    print(f"  Cost per run: {cfg.requests_per_run()} request(s)")
    try:
        client = TrendsClient()
    except MissingKey as exc:
        print(f"✗ {exc}")
        return 1
    # one cheap live call to confirm the key works
    try:
        client.get_top_trends("Google Trends", limit=1)
        print("✓ API key works (live call succeeded)")
    except RateLimited as exc:
        print(f"✓ API key recognized but quota is exhausted: {exc}")
    except TrendsError as exc:
        print(f"✗ API check failed: {exc}")
        return 1
    print(f"  Channels configured: {', '.join(configured_channels()) or 'none'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # -c/--config is shared so it works both before AND after the subcommand
    # (e.g. `trendwatch -c x.yml run` and `trendwatch run -c x.yml` both work).
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("-c", "--config", default=argparse.SUPPRESS, help="path to config.yml")

    parser = argparse.ArgumentParser(
        prog="trendwatch",
        description="Free trend monitoring & breakout alerts.",
        parents=[base],
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run", help="check trends and send alerts", parents=[base]).set_defaults(func=cmd_run)
    sub.add_parser("quota", help="estimate monthly API usage", parents=[base]).set_defaults(func=cmd_quota)
    sub.add_parser("test", help="send a test alert to all configured channels", parents=[base]).set_defaults(func=cmd_test)
    sub.add_parser("check", help="validate config + API key", parents=[base]).set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    args.config = getattr(args, "config", None)
    if not getattr(args, "func", None):
        args.func = cmd_run  # default to run

    try:
        return args.func(args)
    except MissingKey as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    except RateLimited as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
