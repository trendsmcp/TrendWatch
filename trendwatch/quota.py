"""Estimate monthly API usage so a forker stays inside the free tier (100/mo).

The free tier is 100 requests/month. Each run spends 1 request per
(keyword x source) on the watchlist. This module projects monthly usage from the
config + how often the workflow runs, and tells the user to slow down or upgrade
if they'd blow the cap.
"""
from __future__ import annotations

from .config import Config

FREE_TIER_MONTHLY = 100
PRICING_URL = "https://trendsmcp.ai/pricing"

# rough runs-per-month for common cron cadences
CADENCE_RUNS = {
    "hourly": 24 * 30,
    "every 6 hours": 4 * 30,
    "every 12 hours": 2 * 30,
    "daily": 30,
    "every 2 days": 15,
    "weekdays": 22,
    "weekly": 4,
}


def estimate(cfg: Config, runs_per_month: int = 30) -> dict:
    per_run = cfg.requests_per_run()
    monthly = per_run * runs_per_month
    return {
        "per_run": per_run,
        "runs_per_month": runs_per_month,
        "monthly": monthly,
        "free_tier": FREE_TIER_MONTHLY,
        "within_free_tier": monthly <= FREE_TIER_MONTHLY,
    }


def print_report(cfg: Config) -> None:
    per_run = cfg.requests_per_run()

    print("TrendWatch quota estimate")
    print("=" * 40)
    print(f"Watchlist calls per run : {per_run}  ({len(cfg.watchlist)} keyword(s))")
    print(f"Total per run           : {per_run} request(s)")
    print(f"Free tier               : {FREE_TIER_MONTHLY} requests / month")
    print("-" * 40)
    print("Projected monthly usage by schedule:")
    safe_cadence = None
    for label, runs in CADENCE_RUNS.items():
        monthly = per_run * runs
        status = "OK " if monthly <= FREE_TIER_MONTHLY else "OVER"
        if monthly <= FREE_TIER_MONTHLY and safe_cadence is None:
            safe_cadence = label
        print(f"  {label:<16} ~{monthly:>5} req/mo  [{status}]")
    print("-" * 40)
    if per_run == 0:
        print("Your config has nothing to watch. Add keywords or feeds in config.yml.")
    elif per_run > FREE_TIER_MONTHLY:
        print(f"⚠ A single run already costs {per_run} requests. Trim config.yml or upgrade: {PRICING_URL}")
    else:
        fastest_free = max((l for l, r in CADENCE_RUNS.items() if per_run * r <= FREE_TIER_MONTHLY),
                           key=lambda l: CADENCE_RUNS[l], default="weekly")
        print(f"✓ On the free tier you can run up to: {fastest_free}.")
        print(f"  Want more keywords or hourly checks? Upgrade: {PRICING_URL}")
