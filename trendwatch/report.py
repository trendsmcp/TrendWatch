"""Build the shareable artifacts: a dated Markdown report and a live README block.

The README block turns the repo's own front page into a living trend dashboard
(updated by the scheduled workflow) - a screenshot-worthy, link-worthy artifact,
which is exactly the kind of thing that earns stars and backlinks.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from .monitor import Event

README_START = "<!--TRENDWATCH:START-->"
README_END = "<!--TRENDWATCH:END-->"
REPORTS_DIR = Path("reports")
README_PATH = Path("README.md")
CARD_PATH = REPORTS_DIR / "latest.svg"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _esc(text: str, limit: int = 46) -> str:
    """XML-escape and truncate a string for safe embedding in SVG <text>."""
    s = str(text)
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return html.escape(s, quote=True)


def build_svg_card(events: list[Event], leaderboards: dict[str, list]) -> str:
    """Render a dependency-free, on-brand SVG 'trend card'.

    Renders as an image on GitHub and is easy to screenshot/share - every share
    is a tiny ad. No external libraries, so it runs anywhere CI does.
    """
    breakouts = [e for e in events if e.kind == "breakout"][:5]
    feed, names = (next(iter(leaderboards.items())) if leaderboards else ("", []))
    board = names[:6]

    W = 860
    y = 92  # cursor after header
    rows: list[str] = []

    rows.append('<text x="40" y="132" font-size="17" font-weight="700" fill="#7fe9bf">'
                'BREAKOUTS</text>')
    y = 150
    if breakouts:
        for e in breakouts:
            kw = _esc(e.extra.get("keyword", e.title), 34)
            growth = e.extra.get("growth")
            period = e.extra.get("period", "")
            metric = f"+{growth:.0f}% / {period}" if isinstance(growth, (int, float)) else ""
            rows.append(f'<text x="44" y="{y}" font-size="19" fill="#dbe7e1">▲</text>')
            rows.append(f'<text x="44" y="{y}" font-size="19" fill="#2ecf8e">▲</text>')
            rows.append(f'<text x="70" y="{y}" font-size="19" font-weight="700" fill="#f4fbf8">{kw}</text>')
            rows.append(f'<text x="{W-40}" y="{y}" font-size="19" font-weight="700" '
                        f'fill="#5be5a8" text-anchor="end">{_esc(metric, 24)}</text>')
            y += 34
    else:
        rows.append(f'<text x="44" y="{y}" font-size="18" fill="#8aa49a">'
                    f'All quiet - no watchlist breakouts this run.</text>')
        y += 34

    y += 12
    if board:
        rows.append(f'<text x="40" y="{y}" font-size="17" font-weight="700" fill="#7fe9bf">'
                    f'{_esc(feed.upper(), 40)} - TRENDING NOW</text>')
        y += 28
        for i, name in enumerate(board, start=1):
            rows.append(f'<text x="44" y="{y}" font-size="18" fill="#6f857d">{i}</text>')
            rows.append(f'<text x="74" y="{y}" font-size="18" fill="#dbe7e1">{_esc(name, 60)}</text>')
            y += 30

    height = y + 56
    body = "\n  ".join(rows)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="TrendWatch report">
  <defs>
    <linearGradient id="lg" x1="2" y1="20" x2="22" y2="4" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#2ecf8e"/><stop offset="40%" stop-color="#5be5a8"/>
      <stop offset="78%" stop-color="#b8f5d8"/><stop offset="100%" stop-color="#ffffff"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{height}" rx="18" fill="#061410"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{height-1}" rx="18" fill="none" stroke="#15392a"/>
  <g transform="translate(40,34) scale(1.5)">
    <path d="M20.684 4.042A1.029 1.029 0 0 1 22 5.03l-.001 5.712a1.03 1.03 0 0 1-1.647.823L18.71 10.33l-4.18 5.568a1.647 1.647 0 0 1-2.155.428l-.15-.1-3.337-2.507-4.418 5.885c-.42.56-1.185.707-1.777.368l-.144-.095a1.372 1.372 0 0 1-.368-1.776l.095-.144 5.077-6.762a1.646 1.646 0 0 1 2.156-.428l.149.1 3.336 2.506 3.522-4.69-1.647-1.237a1.03 1.03 0 0 1 .194-1.76l.137-.05 5.485-1.595-.001.001z" fill="url(#lg)"/>
  </g>
  <text x="92" y="52" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="26" font-weight="800" fill="#f4fbf8">TrendWatch</text>
  <text x="{W-40}" y="52" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="15" fill="#6f857d" text-anchor="end">{_esc(_now(), 30)}</text>
  <line x1="40" y1="74" x2="{W-40}" y2="74" stroke="#13352700" />
  <g font-family="Segoe UI, Helvetica, Arial, sans-serif">
  {body}
  </g>
  <text x="40" y="{height-22}" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="14" fill="#54655e">Powered by Trends MCP · trendsmcp.ai</text>
</svg>
'''


def build_markdown(events: list[Event], leaderboards: dict[str, list]) -> str:
    breakouts = [e for e in events if e.kind == "breakout"]
    trending = [e for e in events if e.kind == "trending"]

    lines = [f"# 📊 TrendWatch report - {_now()}", ""]

    if breakouts:
        lines.append("## 🚀 Watchlist breakouts")
        lines.append("")
        for e in breakouts:
            lines.append(f"- {e.detail.replace('*', '**')}")
        lines.append("")

    if trending:
        lines.append("## 🆕 Newly trending")
        lines.append("")
        for e in trending:
            lines.append(f"- {e.detail.replace('*', '**')}")
        lines.append("")

    if not breakouts and not trending:
        lines.append("_No breakouts or new entrants since the last run. All quiet._")
        lines.append("")

    for feed, names in leaderboards.items():
        lines.append(f"## 🔝 {feed} - top {len(names)}")
        lines.append("")
        for i, name in enumerate(names, start=1):
            lines.append(f"{i}. {name}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by [TrendWatch](https://github.com/topics/trendwatch) · "
                 "data by [Trends MCP](https://www.trendsmcp.ai)*")
    return "\n".join(lines)


def write_reports(markdown: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "latest.md").write_text(markdown, encoding="utf-8")
    dated = REPORTS_DIR / f"{datetime.now(timezone.utc):%Y-%m-%d}.md"
    dated.write_text(markdown, encoding="utf-8")
    print(f"  ✓ wrote {REPORTS_DIR / 'latest.md'} and {dated}")


def write_svg_card(events: list[Event], leaderboards: dict[str, list]) -> None:
    """Write the shareable SVG trend card (latest + dated archive)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    svg = build_svg_card(events, leaderboards)
    CARD_PATH.write_text(svg, encoding="utf-8")
    dated = REPORTS_DIR / f"{datetime.now(timezone.utc):%Y-%m-%d}.svg"
    dated.write_text(svg, encoding="utf-8")
    print(f"  ✓ wrote {CARD_PATH} (shareable card)")


def _readme_block(events: list[Event], leaderboards: dict[str, list]) -> str:
    breakouts = [e for e in events if e.kind == "breakout"]
    lines = [README_START, "", f"### 📊 Live trends - updated {_now()}", ""]
    # shareable visual card first (renders as an image, easy to screenshot/share)
    lines.append(f'<img src="reports/latest.svg" alt="Latest TrendWatch trends" width="600">')
    lines.append("")

    if breakouts:
        lines.append("**🚀 Breakouts on the watchlist**")
        lines.append("")
        for e in breakouts:
            lines.append(f"- {e.detail.replace('*', '**')}")
        lines.append("")

    # show one compact leaderboard so the README always has something live
    if leaderboards:
        feed, names = next(iter(leaderboards.items()))
        top = names[:10]
        lines.append(f"**🔝 {feed} right now**")
        lines.append("")
        lines.append(" · ".join(f"`{n}`" for n in top))
        lines.append("")

    lines.append("<sub>Auto-updated by TrendWatch · powered by "
                 "[Trends MCP](https://www.trendsmcp.ai)</sub>")
    lines.append("")
    lines.append(README_END)
    return "\n".join(lines)


def update_readme(events: list[Event], leaderboards: dict[str, list]) -> None:
    if not README_PATH.exists():
        return
    content = README_PATH.read_text(encoding="utf-8")
    if README_START not in content or README_END not in content:
        print("  · README has no TRENDWATCH markers; skipping live-dashboard update.")
        return
    block = _readme_block(events, leaderboards)
    before = content.split(README_START)[0]
    after = content.split(README_END)[1]
    README_PATH.write_text(before + block + after, encoding="utf-8")
    print("  ✓ updated README live-dashboard block")
