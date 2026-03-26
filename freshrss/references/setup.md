# FreshRSS Skill Setup

## 1. Create venv and install dependencies

```bash
cd <skills目录>/freshrss/scripts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 2. Enable and identify the API

Make sure FreshRSS API access is enabled on your instance.

Typical endpoints:

- API index: `http://your-host:port/api/`
- Google Reader API: `http://your-host:port/api/greader.php`
- Fever API: `http://your-host:port/api/fever.php`

This skill uses the Google Reader compatible API.

## 3. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- `FRESHRSS_USERNAME` — FreshRSS username
- `FRESHRSS_API_PASSWORD` — recommended API password
- `FRESHRSS_PASSWORD` — compatibility fallback when you do not use a separate API password
- `FRESHRSS_API_URL` — exact Google Reader API endpoint, recommended when API host differs from the site host
- `FRESHRSS_URL` — FreshRSS site base URL; if `FRESHRSS_API_URL` is absent, the client derives `/api/greader.php` from this value

Example:

```dotenv
FRESHRSS_URL=http://192.168.2.200:1201
FRESHRSS_API_URL=http://192.168.2.200:1201/api/greader.php
FRESHRSS_USERNAME=ai
FRESHRSS_API_PASSWORD=2102810019
```

## 4. Verify basic connectivity

```bash
.venv/bin/python freshrss_cli.py list-feeds
.venv/bin/python freshrss_cli.py unread-count
.venv/bin/python freshrss_cli.py get-articles --unread --count 3
```

## 5. Verify unread state consistency

Choose one unread article from `get-articles --unread --count 3`, then test:

```bash
.venv/bin/python freshrss_cli.py mark-read <article_id>
.venv/bin/python freshrss_cli.py mark-unread <article_id>
```

If both commands return `OK`, the read/unread API flow is working.

## 6. Troubleshooting

- If you see `FreshRSS API 地址不可用`, re-check `FRESHRSS_API_URL` or `FRESHRSS_URL`.
- If you see `FreshRSS API 认证失败`, verify username/password and prefer `FRESHRSS_API_PASSWORD`.
- If the API is reachable in a browser but the CLI still fails, test the Google Reader endpoint directly and confirm it is not blocked by a reverse proxy.
