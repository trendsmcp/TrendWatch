# Changelog

All notable changes to TrendWatch are documented here.

## [1.1.0] - 2026-06-07
### Changed
- **Focused on keyword alerts.** Removed the top-trends / discovery leaderboard feature - TrendWatch now does one thing well: watch your keywords and alert on breakouts.
- **Removed request retries.** Each API call is a single attempt now, so a failed call fails fast instead of quietly spending your free-tier quota.

## [1.0.0] - 2026-06-07
### Added
- 🚀 First public release.
- **Watchlist breakout detection** - flag keywords whose short-window growth clears a threshold.
- **Discovery radar** - surface items newly entering live leaderboards (Google Trends, TikTok, YouTube, Reddit, Amazon, and more).
- **Multi-channel alerts** - Slack, Discord, Telegram, email (SMTP), and generic webhook. Each activates only when its secret is set.
- **Live README dashboard** - auto-updates a trend block on every run.
- **Dated Markdown reports** committed back to `reports/`.
- **Quota estimator** (`python -m trendwatch quota`) to stay inside the free tier.
- CLI: `run`, `check`, `test`, `quota`.
- One-click **"Use this template"** setup; runs free on GitHub Actions.
