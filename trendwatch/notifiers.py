"""Send alerts to whichever channels the user configured via secrets.

Each channel activates only when its environment variable(s) are present, so a
forker can wire up just Slack, just Telegram, all of them, or none (console only).
Nothing here ever raises: a broken channel logs a warning and the run continues.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.text import MIMEText

import requests

from .monitor import Event

TIMEOUT = 15


def _md_to_plain(text: str) -> str:
    return text.replace("*", "")


def _build_summary(events: list[Event]) -> tuple[str, str]:
    """Return (heading, body_markdown) for a batch of events."""
    breakouts = [e for e in events if e.kind == "breakout"]
    trending = [e for e in events if e.kind == "trending"]
    parts = []
    if breakouts:
        parts.append(f"{len(breakouts)} breakout(s)")
    if trending:
        parts.append(f"{len(trending)} newly trending")
    heading = "📊 TrendWatch: " + ", ".join(parts) if parts else "📊 TrendWatch"

    lines = []
    if breakouts:
        lines.append("*Breakouts on your watchlist*")
        lines.extend(f"• {e.detail}" for e in breakouts)
    if trending:
        if lines:
            lines.append("")
        lines.append("*Newly trending*")
        lines.extend(f"• {e.detail}" for e in trending[:25])
    lines.append("")
    lines.append("_Powered by Trends MCP — https://www.trendsmcp.ai_")
    return heading, "\n".join(lines)


# --- individual channels -------------------------------------------------
def _notify_slack(heading: str, body: str) -> None:
    url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        return
    text = f"*{heading}*\n{body}"
    resp = requests.post(url, json={"text": text}, timeout=TIMEOUT)
    resp.raise_for_status()
    print("  ✓ sent to Slack")


def _notify_discord(heading: str, body: str) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        return
    # Discord uses ** for bold; our markdown already uses * so bold it up a level.
    content = f"**{heading}**\n{body}".replace("*", "**").replace("****", "**")
    if len(content) > 1900:
        content = content[:1900] + "\n…"
    resp = requests.post(url, json={"content": content}, timeout=TIMEOUT)
    resp.raise_for_status()
    print("  ✓ sent to Discord")


def _notify_telegram(heading: str, body: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat_id):
        return
    text = f"*{heading}*\n{body}"
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    print("  ✓ sent to Telegram")


def _notify_email(heading: str, body: str) -> None:
    host = os.environ.get("SMTP_HOST", "").strip()
    to_addr = os.environ.get("SMTP_TO", "").strip()
    if not (host and to_addr):
        return
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()

    msg = MIMEText(_md_to_plain(body), "plain", "utf-8")
    msg["Subject"] = _md_to_plain(heading)
    msg["From"] = user or "trendwatch@localhost"
    msg["To"] = to_addr

    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=TIMEOUT) as server:
            if user:
                server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=TIMEOUT) as server:
            server.starttls(context=context)
            if user:
                server.login(user, password)
            server.send_message(msg)
    print("  ✓ sent Email")


def _notify_webhook(heading: str, body: str, events: list[Event]) -> None:
    url = os.environ.get("GENERIC_WEBHOOK_URL", "").strip()
    if not url:
        return
    payload = {
        "heading": heading,
        "text": _md_to_plain(body),
        "events": [
            {"kind": e.kind, "title": e.title, "source": e.source, "detail": _md_to_plain(e.detail), **e.extra}
            for e in events
        ],
    }
    resp = requests.post(url, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    print("  ✓ sent to webhook")


CHANNELS = {
    "Slack": lambda h, b, e: _notify_slack(h, b),
    "Discord": lambda h, b, e: _notify_discord(h, b),
    "Telegram": lambda h, b, e: _notify_telegram(h, b),
    "Email": lambda h, b, e: _notify_email(h, b),
    "Webhook": lambda h, b, e: _notify_webhook(h, b, e),
}


def configured_channels() -> list[str]:
    active = []
    if os.environ.get("SLACK_WEBHOOK_URL"):
        active.append("Slack")
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        active.append("Discord")
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        active.append("Telegram")
    if os.environ.get("SMTP_HOST") and os.environ.get("SMTP_TO"):
        active.append("Email")
    if os.environ.get("GENERIC_WEBHOOK_URL"):
        active.append("Webhook")
    return active


def dispatch(events: list[Event]) -> None:
    """Send a batch of events to every configured channel."""
    if not events:
        print("No alerts to send this run.")
        return
    heading, body = _build_summary(events)

    # always print to the Actions log
    print("\n" + heading)
    print(_md_to_plain(body))

    for name, fn in CHANNELS.items():
        try:
            fn(heading, body, events)
        except Exception as exc:  # never let one channel break the others
            print(f"  ! {name} notification failed: {exc}")


def send_test() -> None:
    """Fire a harmless test alert through every configured channel."""
    demo = [
        Event(
            kind="breakout",
            title="trendwatch test",
            detail="📈 *TrendWatch test alert* — if you can read this, your channel works!",
            source="self-test",
            score=100,
        )
    ]
    active = configured_channels()
    print(f"Configured channels: {', '.join(active) if active else 'none (console only)'}")
    dispatch(demo)
