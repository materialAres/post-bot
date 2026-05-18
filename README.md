# post-bot

A Python bot that monitors Instagram accounts for new posts and forwards each post's image and caption to a Telegram chat. It runs on a schedule via GitHub Actions and requires no always-on server.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Prerequisites](#2-prerequisites)
3. [Local Setup](#3-local-setup)
4. [Generating the Instagram Session File](#4-generating-the-instagram-session-file)
5. [Creating a Telegram Bot](#5-creating-a-telegram-bot)
6. [GitHub Actions Setup](#6-github-actions-setup)
7. [Modifying the Schedule](#7-modifying-the-schedule)
8. [Manual Trigger](#8-manual-trigger)
9. [How Deduplication Works](#9-how-deduplication-works)

---

## 1. Project Overview

post-bot polls one or more Instagram profiles using [instaloader](https://instaloader.github.io/), filters posts published today (UTC), and sends each one to a Telegram chat via the [python-telegram-bot](https://python-telegram-bot.org/) library.

Key design decisions:

- **Deduplication** — post shortcodes that have already been forwarded are persisted in `sent_posts.json`. Re-runs skip any shortcode already present in that file.
- **Session persistence** — instaloader's session is saved to `session.txt` after the first successful login. In GitHub Actions this file is restored from a base64-encoded secret on every run, avoiding repeated credential-based logins that could trigger Instagram rate limits or 2FA prompts.

---

## 2. Prerequisites

### Tools

| Tool | Version |
|------|---------|
| Python | 3.13 or later |
| pip | bundled with Python |
| Git | any recent version |
| A GitHub account | required for Actions |

### Accounts

- **Instagram account** — the account whose credentials are used to authenticate with instaloader. This does not have to be one of the monitored profiles.
- **Telegram account** — needed to create a bot via BotFather and to obtain your personal chat ID.

---

## 3. Local Setup

### Clone the repository

```bash
git clone https://github.com/<your-username>/post-bot.git
cd post-bot
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create a `.env` file

Create a file named `.env` in the project root. The script loads it automatically via `python-dotenv`.

```dotenv
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
PROFILES_LIST=profile1,profile2,profile3
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_ID=987654321
```

### Environment variables reference

| Variable | Description |
|----------|-------------|
| `INSTAGRAM_USERNAME` | Username of the Instagram account used to authenticate with instaloader. |
| `INSTAGRAM_PASSWORD` | Password for that account. Used only when no valid `session.txt` exists. |
| `PROFILES_LIST` | Comma-separated list of Instagram usernames to monitor (e.g. `nasa,natgeo`). |
| `BOT_TOKEN` | The token issued by BotFather when you created your Telegram bot. |
| `TELEGRAM_ID` | The numeric ID of the Telegram chat (personal or group) that receives the posts. |

---

## 4. Generating the Instagram Session File

Running the bot locally at least once creates a `session.txt` file that can be reused in GitHub Actions to avoid repeated password-based logins.

### Run the bot locally

```bash
python main.py
```

On the first run, instaloader logs in with your credentials and writes the session to `session.txt`. Subsequent runs load the session from that file instead.

If the account has two-factor authentication enabled, you will be prompted to enter the 2FA code in the terminal during this first run.

### Encode the session file for GitHub Secrets

GitHub Secrets only accept text values, so encode `session.txt` as base64:

```bash
base64 -w 0 session.txt
```

Copy the entire output string — you will paste it as the value of the `INSTAGRAM_SESSION_B64` secret in the next section.

> **Note:** `-w 0` disables line wrapping so the output is a single line, which is required by the Actions decode step.

---

## 5. Creating a Telegram Bot

### Create the bot

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts (choose a display name, then a username ending in `bot`).
3. BotFather will reply with a token in the format `123456789:ABCdef...`. This is your `BOT_TOKEN`.

### Retrieve your chat ID

The `TELEGRAM_ID` is the numeric identifier of the chat where the bot will send messages.

1. Open Telegram and start a conversation with **@userinfobot** (send it any message).
2. It replies instantly with your numeric chat ID — that value is your `TELEGRAM_ID`.

---

## 6. GitHub Actions Setup

### Required secrets

Navigate to your repository on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**, and add each of the following:

| Secret | Description |
|--------|-------------|
| `INSTAGRAM_USERNAME` | Instagram account username passed to `main.py` at runtime. |
| `INSTAGRAM_PASSWORD` | Instagram account password. Used as a fallback if session restoration fails. |
| `INSTAGRAM_SESSION_B64` | Base64-encoded contents of `session.txt` (see [Section 4](#4-generating-the-instagram-session-file)). Decoded back to `session.txt` before the bot runs. |
| `PROFILES_LIST` | Comma-separated Instagram usernames to monitor. |
| `BOT_TOKEN` | Telegram bot token from BotFather. |
| `TELEGRAM_ID` | Numeric Telegram chat ID that receives the forwarded posts. |

### How `sent_posts.json` is persisted

The workflow uses the `actions/cache` step to persist `sent_posts.json` across runs:

```yaml
- name: Restore sent posts cache
  uses: actions/cache@v5
  with:
    path: sent_posts.json
    key: sent-posts-${{ github.run_id }}
    restore-keys: sent-posts-
```

On each run the most recently saved `sent_posts.json` is restored before the bot executes, ensuring previously sent shortcodes are not forwarded again.

---

## 7. Modifying the Schedule

The workflow is triggered by two cron expressions defined at the top of `.github/workflows/post-bot.yml`:

```yaml
on:
  schedule:
    # Runs at 11:00 AM — adjust for your timezone (times are UTC)
    - cron: '0 9 * * *'
    # Runs at 11:40 PM — adjust for your timezone (times are UTC)
    - cron: '40 21 * * *'
```

Edit these two lines to change when the bot runs. GitHub Actions cron uses standard UTC-based cron syntax:

```
┌─ minute  (0–59)
│  ┌─ hour  (0–23, UTC)
│  │  ┌─ day of month  (1–31)
│  │  │  ┌─ month  (1–12)
│  │  │  │  ┌─ day of week  (0–7, 0 and 7 = Sunday)
│  │  │  │  │
*  *  *  *  *
```

### Timezone conversion examples

| Local time | Timezone | UTC cron expression |
|------------|----------|---------------------|
| 10:00 | CET (UTC+1) | `0 9 * * *` |
| 10:00 | CEST (UTC+2, summer) | `0 8 * * *` |
| 10:00 | EST (UTC−5) | `0 15 * * *` |
| 10:00 | PST (UTC−8) | `0 18 * * *` |
| 10:00 | JST (UTC+9) | `0 1 * * *` |

> **GitHub Actions cron note:** Scheduled workflows may run a few minutes late during periods of high load. The minimum supported interval is every 5 minutes.

---

## 8. Manual Trigger

The workflow includes a `workflow_dispatch` event, which means it can be started on demand from the GitHub Actions UI without waiting for the next scheduled run.

1. Go to your repository on GitHub.
2. Click the **Actions** tab.
3. Select **Post Bot** from the workflow list on the left.
4. Click **Run workflow** → **Run workflow**.

This is useful for testing configuration changes or forcing an immediate check after adding new profiles.

---

## 9. How Deduplication Works

Every time a post is successfully forwarded to Telegram, its Instagram shortcode (the unique identifier visible in the post URL, e.g. `C1a2B3cD4eF`) is added to `sent_posts.json`:

```json
["C1a2B3cD4eF", "Dg5Hi6jK7lM", "En8Op9qR0sT"]
```

At the start of each run, `load_sent_shortcodes()` reads this file into a Python `set`. After fetching today's posts, any post whose shortcode is already in the set is filtered out before sending:

```python
new_posts = [p for p in today_posts if p.shortcode not in sent_shortcodes]
```

Once the new posts are sent, the set is updated and written back to disk by `save_sent_shortcodes()`. The `actions/cache` step then saves this file so it is available on the next run.

This means that even if the workflow runs multiple times on the same day (e.g. via a manual trigger), each post is forwarded exactly once.
