# FreshRSS Skill Setup

## 1. Create venv and install dependencies

```bash
cd <skills目录>/freshrss
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `FRESHRSS_URL` — Your FreshRSS instance URL (e.g. https://rss.example.com)
- `FRESHRSS_USERNAME` — Your login username
- `FRESHRSS_PASSWORD` — Your login password

## 3. Verify

```bash
.venv/bin/python freshrss_cli.py list-feeds
```

You should see a list of your subscribed feeds. If you get an authentication error, double-check your credentials in `.env`.
