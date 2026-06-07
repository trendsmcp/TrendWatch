"""Core monitoring logic: flag watchlist keywords whose growth clears the threshold."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .client import RateLimited, TrendsClient
from .config import Config


@dataclass
class Event:
    kind: str          # "breakout"
    title: str         # short headline
    detail: str        # human-readable line
    source: str        # data source
    score: float = 0.0  # growth %, used for sorting
    extra: dict = field(default_factory=dict)


def _emoji_for_growth(pct: float) -> str:
    if pct >= 200:
        return "🚀"
    if pct >= 100:
        return "🔥"
    if pct >= 50:
        return "📈"
    return "↗️"


def check_watchlist(client: TrendsClient, cfg: Config) -> list[Event]:
    """For each watched keyword, flag a breakout when short-window growth clears the threshold."""
    events: list[Event] = []
    periods = [cfg.breakout_period] + [p for p in cfg.context_periods if p != cfg.breakout_period]

    for item in cfg.watchlist:
        for source in item.sources:
            try:
                resp = client.get_growth(source, item.keyword, periods)
            except RateLimited:
                raise  # quota hit: stop and let the runner send the upgrade nudge
            except Exception as exc:  # one bad keyword shouldn't kill the run
                print(f"  ! growth failed for '{item.keyword}' [{source}]: {exc}")
                continue

            results = {r.get("period"): r for r in resp.get("results", []) if r.get("status") == "success"}
            primary = results.get(cfg.breakout_period)
            if not primary:
                continue

            growth = float(primary.get("growth", 0) or 0)
            direction = primary.get("direction")
            if direction == "increase" and growth >= cfg.breakout_threshold:
                context = []
                for p in cfg.context_periods:
                    r = results.get(p)
                    if r:
                        sign = "+" if r.get("direction") == "increase" else "-"
                        context.append(f"{p} {sign}{abs(float(r.get('growth', 0))):.0f}%")
                ctx = f"  ({', '.join(context)})" if context else ""
                emoji = _emoji_for_growth(growth)
                events.append(
                    Event(
                        kind="breakout",
                        title=item.keyword,
                        detail=f"{emoji} *{item.keyword}* is breaking out on {source}: "
                        f"+{growth:.0f}% over {cfg.breakout_period}{ctx}",
                        source=source,
                        score=growth,
                        extra={
                            "keyword": item.keyword,
                            "growth": growth,
                            "period": cfg.breakout_period,
                            "recent_value": primary.get("recent_value"),
                            "baseline_value": primary.get("baseline_value"),
                        },
                    )
                )
    return events


def run_monitor(client: TrendsClient, cfg: Config, state: dict[str, Any]) -> list[Event]:
    """Run the watchlist detector. Returns events and mutates state in place."""
    print(f"Watching {len(cfg.watchlist)} keyword(s)...")

    events = check_watchlist(client, cfg)

    # de-dupe repeated breakout alerts within the same day
    breakouts_state = state.setdefault("breakouts", {})
    today = date.today().isoformat()
    deduped: list[Event] = []
    for ev in events:
        key = f"{ev.extra.get('keyword')}|{ev.source}"
        if breakouts_state.get(key) == today:
            continue
        breakouts_state[key] = today
        deduped.append(ev)

    deduped.sort(key=lambda e: e.score, reverse=True)
    return deduped
