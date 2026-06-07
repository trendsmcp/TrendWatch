"""Load and validate config.yml - the single file forkers edit."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = os.environ.get("TRENDWATCH_CONFIG", "config.yml")


@dataclass
class WatchItem:
    keyword: str
    sources: list[str] = field(default_factory=lambda: ["google search"])


@dataclass
class Config:
    watchlist: list[WatchItem]
    breakout_period: str
    breakout_threshold: float
    context_periods: list[str]
    update_readme: bool
    write_markdown: bool
    raw: dict[str, Any] = field(default_factory=dict)

    # --- quota helpers ---------------------------------------------------
    def requests_per_run(self) -> int:
        """How many API calls a single run consumes (1 per keyword x source)."""
        return sum(len(w.sources) for w in self.watchlist)


def load_config(path: str | None = None) -> Config:
    cfg_path = Path(path or DEFAULT_CONFIG_PATH)
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {cfg_path}. Copy config.yml from the template and edit it."
        )
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    watchlist_raw = data.get("watchlist") or []
    watchlist: list[WatchItem] = []
    for item in watchlist_raw:
        if isinstance(item, str):
            watchlist.append(WatchItem(keyword=item))
        elif isinstance(item, dict) and item.get("keyword"):
            sources = item.get("sources") or item.get("source") or ["google search"]
            if isinstance(sources, str):
                sources = [sources]
            watchlist.append(WatchItem(keyword=str(item["keyword"]), sources=list(sources)))

    breakout = data.get("breakout") or {}
    report = data.get("report") or {}

    return Config(
        watchlist=watchlist,
        breakout_period=str(breakout.get("period", "7D")),
        breakout_threshold=float(breakout.get("threshold_pct", 50)),
        context_periods=[str(p) for p in (breakout.get("also_periods") or ["1M", "3M"])],
        update_readme=bool(report.get("update_readme", True)),
        write_markdown=bool(report.get("write_markdown", True)),
        raw=data,
    )
