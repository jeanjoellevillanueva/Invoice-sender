# Invoice Sender

Dockerized monthly invoice emailer with a small config UI. No database — config and send history live in JSON files.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A Gmail account that can use **App Passwords** (see below)

## Quick start

```bash
git clone https://github.com/jeanjoellevillanueva/Invoice-sender.git
cd Invoice-sender
cp data/config.example.json data/config.json
cp data/sent.example.json data/sent.json
docker compose up -d --build
```

Open **http://localhost:8080/**

### Auto-start on laptop login

1. Docker Desktop → **Settings** → **General** → enable **Start Docker Desktop when you log in**
2. This stack uses `restart: unless-stopped`, so the container comes back when Docker starts

## Gmail SMTP setup

1. Use a Google account that supports App Passwords (personal Gmail usually works; some Workspace accounts block them)
2. Turn on [2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification)
3. Create an App Password at [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. In the UI under **SMTP (Gmail)**:
   - **Username** — your Gmail address
   - **App password** — the 16-character password (spaces optional)
   - **From email / From name** — as you want them to appear
5. Set **Recipient email** and click **Save config**

If Google says *“The setting that you are looking for is not available”*:

- 2-Step Verification may still be off, or
- Your Workspace admin may have disabled App Passwords — use a personal Gmail instead, or ask the admin to allow App Passwords

## Config files

| File | Purpose |
|------|---------|
| `data/config.json` | Local settings (SMTP, amount, invoice details). **Not committed** — keep secrets here |
| `data/config.example.json` | Template without passwords |
| `data/sent.json` | Months already sent (kept to last 12). **Not committed** |
| `generated/` | PDF copies of sent invoices |

## Behaviour

- **Cron / scheduler:** checks hourly. From the configured send day (default **25**) through month end, sends **once for the current month** if that month is not in `sent.json`
- **Catch-up:** if the laptop was off on the 25th, it still sends later that month when Docker is running again
- **Manual send:** pick any of the last 12 months (e.g. a missed June) and send; use **Force resend** only if that month was already recorded

## Useful commands

```bash
docker compose up -d --build   # start / rebuild
docker compose ps              # status
docker compose logs -f         # logs
docker compose down            # stop
```

Default port is `8080`. To avoid clashes with other projects, change the left side in `docker-compose.yml`, e.g. `"8081:8080"`.
