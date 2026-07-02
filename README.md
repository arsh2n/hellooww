# Proxy Shop Telegram Bot

A Telegram bot for selling proxy packages with Paytm/UPI payment flow, deployable on Railway via GitHub.

---

## Features

- Catalogue image with package buttons
- Selecting a package shows its product photo with **Buy Now** / **Back** buttons
- **Buy Now** generates a Paytm/UPI payment QR on the fly (via `UPI_ID` + `MERCHANT_NAME`, amount pre-filled) — no per-option hardcoded QR images needed
- **Back** returns to the catalogue
- Graceful fallback to support contact if no payment proof sent

---

## Project Structure

```
├── bot.py            ← main bot
├── requirements.txt
├── Procfile
├── railway.toml
├── .env.example      ← copy to .env for local dev
└── README.md
```

---

## Step 1 — Create your Telegram bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the **BOT_TOKEN** you receive

---

## Step 2 — Add your images directly in bot.py

Images are hardcoded in `bot.py`, not set via Railway variables.

1. `CATALOGUE_PHOTO` (top of `bot.py`) — your main catalogue image
2. `OPTION_IMAGES` (below `OPTION_PRICES`) — one list per option key; add one URL for a single photo, or 2+ URLs to send them as an album
3. Use a public HTTPS image URL, or a Telegram file_id (send the image to your bot once and grab the file_id from the logs — faster to load)

---

## Step 3 — Deploy to Railway

### 3a. Push to GitHub

```bash
git init
git add .
git commit -m "init proxy bot"
gh repo create proxy-bot --private --push --source=.
# or push manually to an existing GitHub repo
```

### 3b. Create Railway project

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**
2. Select your repo

### 3c. Set environment variables

In Railway → your service → **Variables**, add:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | `123456789:ABCxxx` |
| `UPI_ID` | Your Paytm/UPI merchant ID, e.g. `merchant@paytm` |
| `MERCHANT_NAME` | Your business name (shown to the payer's UPI app) |
| `DEMO_CHANNEL` | `https://t.me/your_demo_channel` |
| `SUPPORT` | `@yoursupporthandle` |
| `WEBHOOK_URL` | *(leave blank for now — fill in step 3d)* |

Images (`CATALOGUE_PHOTO`, `OPTION_IMAGES`) are edited directly in `bot.py` — see Step 2 — so just commit and push after editing them.

### 3d. Set WEBHOOK_URL after first deploy

1. After Railway deploys, copy the generated domain (e.g. `https://myproxybot.up.railway.app`)
2. Add it as `WEBHOOK_URL` in Variables
3. Railway will auto-redeploy

---

## Local Development

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in your values (leave WEBHOOK_URL blank)
python bot.py             # runs in polling mode locally
```

---

## Customising Package Names

Edit `OPTION_NAMES`, `OPTION_PRICES`, and `OPTION_IMAGES` in `bot.py` to configure your packages:

```python
OPTION_NAMES = {
    "A": "Starter Pack – 10 Proxies",
    "B": "Basic Pack – 25 Proxies",
    "C": "Standard Pack – 50 Proxies",
    ...
}

OPTION_PRICES = {
    "A": 59,   # rupees, used both for display and the UPI QR amount
    ...
}

OPTION_IMAGES = {
    "A": ["https://example.com/a1.jpg"],                          # single photo
    "B": ["https://example.com/b1.jpg", "https://example.com/b2.jpg"],  # sent as an album
    ...
}
```

---

## Notes

- Railway sets `PORT` automatically — don't override it
- Without `CATALOGUE_PHOTO` / an option's `OPTION_IMAGES` entry set, the bot falls back to text messages so it always works
- Without `UPI_ID` set, Buy Now falls back to a "contact support" message instead of a QR
- Images live in `bot.py`, so pushing a new image means committing and redeploying (not just changing a Railway variable)
- Each user's conversation state is tracked independently (`per_user=True`)
- `/cancel` resets a session at any point
