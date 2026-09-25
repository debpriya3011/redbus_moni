# 🚌 RedBus Route Monitor & Telegram Bot

An automated, serverless bus seat monitor and interactive Telegram bot that tracks real-time RedBus inventory, seat availability (including window & aisle seat breakdown), and fare updates for specific routes and dates.

---

## ✨ Features

- ⏰ **Automated Hourly Monitoring**: Runs every 1 hour via GitHub Actions with zero server maintenance.
- 💺 **Real-Time Seat Breakdown**: Tracks total available seats, window seats (🪟), and aisle seats (🚶).
- 🔗 **Direct One-Click Booking**: Generates direct deep links to the RedBus booking page with route, date, and operator pre-filtered for rapid checkout.
- 🤖 **Interactive Telegram Bot**:
  - **Bottom-Left `Menu` Button**: Native Telegram slash command menu.
  - **Persistent Quick Keyboard**: One-tap buttons (`📊 Status & Buses`, `📅 View Dates`, `⏰ Departure Window`, `ℹ️ Help & Guide`).
- ⚡ **Dynamic Live Configuration**: Add/remove monitored journey dates and adjust departure time windows directly from Telegram chat without touching code.
- 🔄 **Safe State Sync**: State and config are automatically committed and pushed to GitHub with retry and conflict resolution.

---

## 📱 Telegram Commands & Controls

You can control the monitor directly from your Telegram bot chat:

| Command | Description | Example |
| :--- | :--- | :--- |
| **`/status`** | View current route, monitored dates, time window, and matching buses | `/status` |
| **`/dates`** | View current dates or replace the entire monitored dates list | `/dates 15-Oct-2026 16-Oct-2026 24-Oct-2026` |
| **`/add_date`** | Add one or more dates without removing existing ones | `/add_date 27-Sep-2026` |
| **`/remove_date`** | Remove specific date(s) from monitoring | `/remove_date 15-Oct-2026` |
| **`/time`** | Set or view departure time window (`HH:MM` 24h format) | `/time 10:00 16:00` |
| **`/set`** | Configure both dates and departure window in one command | `/set 15-Oct-2026 24-Oct-2026 10:00 16:00` |
| **`/help`** | Show full command guide and examples | `/help` |

> 💡 **Tip**: Multiple date formats are supported (e.g., `24-Oct-2026`, `24/10/2026`, `24-10-2026`, `2026-10-24`) and will automatically normalize to `DD-Mon-YYYY`.

---

## 🚀 Setup & Deployment

### 1. Fork or Clone the Repository
```bash
git clone https://github.com/your-username/redbus-monitor.git
cd redbus-monitor
```

### 2. Configure GitHub Secrets
Go to your GitHub repository ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**:

| Secret Name | Description |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Your Telegram User ID or Group Chat ID (e.g. from [@userinfobot](https://t.me/userinfobot)) |

### 3. Workflow Permissions
In GitHub ➔ **Settings** ➔ **Actions** ➔ **General** ➔ **Workflow permissions**:
- Select **Read and write permissions** (allows the workflow to commit state updates back to `state.json` and `config.json`).

### 4. Running Locally (Optional)
```bash
pip install -r requirements.txt

# On Windows (PowerShell):
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"
python redbus_monitor_telegram.py

# On Linux / macOS:
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python redbus_monitor_telegram.py
```

---

## ⚙️ Configuration Files

- [`config.json`](./config.json): Stores active journey dates, departure window, and Telegram message update offsets.
- [`state.json`](./state.json): Tracks known bus inventory for diffing and vacancy reporting.
- [`.github/workflows/redbus-monitor.yml`](./.github/workflows/redbus-monitor.yml): GitHub Actions workflow scheduled to run hourly (`0 * * * *`) and on-demand via `workflow_dispatch`.

---

## 🛠️ Tech Stack

- **Python 3.11**
- **curl_cffi** (TLS-impersonated browser session for RedBus search API)
- **urllib.request** (Standard HTTP client for Telegram Bot API)
- **GitHub Actions** (Hourly cron automation & state persistence)

---

## 📄 License
MIT License
