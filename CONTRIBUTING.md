# Contributing to TrendWatch

Thanks for helping make TrendWatch better! 🎉

## Ideas that are very welcome
- **New notification channels** (Microsoft Teams, Mattermost, ntfy, Bark, Pushover, SMS…). Add a function in `trendwatch/notifiers.py` and wire it into `CHANNELS` + `configured_channels()`.
- **Smarter detection** (acceleration, anomaly detection, multi-source confirmation).
- **Nicer reports** (charts/sparklines, HTML output, per-feed pages).
- **More presets** and example `config.yml` recipes for specific niches (e-commerce, crypto, SEO, investing).

## Dev setup
```bash
pip install -r requirements.txt
cp .env.example .env   # add your TRENDS_API_KEY (free at https://trendsmcp.ai)
python -m trendwatch check
```

## Guidelines
- Keep dependencies minimal (currently just `requests` + `PyYAML`) so it stays fast and reliable on CI.
- A failing notification channel or a bad keyword should **never** crash a run — log and continue.
- Never commit secrets. Keys belong in `.env` (local) or GitHub Secrets (CI).

## Submitting
1. Fork → branch → commit.
2. Open a PR describing the change and how you tested it.

By contributing you agree your work is licensed under the project's [MIT License](LICENSE).
