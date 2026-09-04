# AllInOneDiscordBot

A feature-complete, production-ready Discord bot written in **Python 3.13+** using **discord.py 2.7+** and **aiosqlite**. Designed for high performance, modular architecture, and 24/7 deployment on Linux servers.

---

## 🌟 Key Features

| Category | Features |
| :--- | :--- |
| 🛡️ **Moderation** | `/kick`, `/ban`, `/unban`, `/timeout`, `/untimeout`, `/warn`, `/warnings`, `/clearwarns`, `/purge`, `/slowmode`, `/lock`, `/unlock` with role hierarchy safety and mod logs. |
| 🤖 **AutoMod** | Automated real-time protection: anti-invite detection, spam rate-limiting, excessive caps suppression, mass-mention filtering, and customizable banned words. |
| 🎫 **Tickets** | Interactive support ticket system featuring Discord buttons, modal intake forms, permission overrides, in-channel controls, and `.txt` transcript exports. |
| 👋 **Welcome & Leave** | Customizable welcome and goodbye embeds, member count updates, and automated join role assignment (`autorole`). |
| 📜 **Server Logs** | Audit logging for message edits, deletions, member nickname/role updates, and channel additions/removals. |
| 🏷️ **Self Roles** | Interactive dropdown menus (`discord.ui.Select`) allowing members to pick and toggle vanity roles. |
| 🏆 **XP & Levels** | Dynamic message XP with cooldowns, level-up announcements, customizable multipliers, `/rank` cards, and `/leaderboard`. |
| 💰 **Economy** | Virtual wallet and bank accounts, `/daily`, `/work` shifts, `/beg`, `/deposit`, `/withdraw`, `/pay`, `/gamble`, `/rob`, and wealth leaderboards. |
| 🎮 **Fun & Games** | Interactive button-based Rock-Paper-Scissors (`/rps`), `/roll`, `/8ball`, `/coinflip`, `/meme`, `/joke`, and `/choose`. |
| 🧮 **Utility** | `/ping` with DB latency diagnostics, `/serverinfo`, `/userinfo`, `/avatar`, `/botinfo`, `/uptime`, and AST-safe math `/calculate`. |
| 📊 **Polls** | Live polling engine with interactive letter buttons, dynamic Unicode progress bars, and `/poll end` summaries. |
| ⚙️ **Configuration** | Easy setup via `/config` to customize mod logs, audit logs, tickets, welcome channels, autoroles, and XP rates. |

---

## 📂 Project Architecture

```
AllInOneDiscordBot/
├── bot.py                  # Core bot entrypoint, lifecycle, and slash sync
├── config.py               # Environment configuration and color constants
├── database.py             # aiosqlite connection manager and schema runner
├── requirements.txt        # Pinned Python package dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Ignores .env, virtualenvs, sqlite databases, logs
├── README.md               # Documentation and Linux deployment guide
├── cogs/                   # Modular extensions
│   ├── __init__.py         # Cog extension manifest
│   ├── moderation.py       # Moderation suite
│   ├── automod.py          # Real-time automated moderation guards
│   ├── tickets.py          # Interactive ticket panels and modals
│   ├── welcome.py          # Welcome & farewell message listeners
│   ├── logging.py          # Audit logs for edits, deletes, and updates
│   ├── roles.py            # Self-assignable role menus
│   ├── levels.py           # XP progression and rank cards
│   ├── economy.py          # Currency, banking, daily rewards, and casino
│   ├── fun.py              # Games, memes, jokes, and dice
│   ├── utility.py          # Diagnostic tools, server/user info, and calculator
│   ├── polls.py            # Real-time button polls
│   └── configuration.py    # Administrative setup commands
├── database/               # Database layer
│   ├── __init__.py
│   ├── schema.py           # SQLite DDL tables and indexes
│   └── repositories.py     # Asynchronous CRUD repository methods
└── utils/                  # Utility helpers
    ├── __init__.py
    ├── checks.py           # Command permission check decorators
    ├── embeds.py           # Standardized embed constructors
    ├── errors.py           # Custom exceptions and error handlers
    ├── permissions.py      # Role hierarchy and permission verifications
    └── helpers.py          # Time parsing, level curves, and string formatters
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.13+** installed on your system.
- A registered Discord Application with a Bot token from the [Discord Developer Portal](https://discord.com/developers/applications).

> **Important Gateway Intents:**
> In the Discord Developer Portal under **Bot** -> **Privileged Gateway Intents**, enable:
> 1. **Server Members Intent** (required for welcome messages, autorole, and rank cards)
> 2. **Message Content Intent** (required for automod filters and XP progression)

---

### 2. Installation & Setup

1. **Clone or copy the project:**
   ```bash
   cd AllInOneDiscordBot
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Linux/macOS
   # or: venv\Scripts\activate # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in your parameters:
   ```ini
   DISCORD_TOKEN=your_bot_token_here
   GUILD_ID=                     # Optional: your Discord server ID for instant dev slash sync
   DATABASE_PATH=data/bot.db
   LOG_LEVEL=INFO
   ```

5. **Start the bot:**
   ```bash
   python bot.py
   ```

---

## 🐧 24/7 Linux Server Deployment (Hoody / Ubuntu / Debian)

To keep the bot running 24/7 in the background with auto-restart on crashes or system reboots, configure a `systemd` service:

1. **Create the service unit file:**
   ```bash
   sudo nano /etc/systemd/system/discordbot.service
   ```

2. **Paste the following template (adjust paths to your user and directory):**
   ```ini
   [Unit]
   Description=AllInOneDiscordBot 24/7 Service
   After=network.target

   [Service]
   Type=simple
   User=hoody
   WorkingDirectory=/home/hoody/AllInOneDiscordBot
   ExecStart=/home/hoody/AllInOneDiscordBot/venv/bin/python bot.py
   Restart=always
   RestartSec=5
   EnvironmentFile=/home/hoody/AllInOneDiscordBot/.env

   [Install]
   WantedBy=multi-user.target
   ```

3. **Reload systemd, enable, and start the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable discordbot
   sudo systemctl start discordbot
   ```

4. **Monitor live logs:**
   ```bash
   journalctl -u discordbot -f
   ```

---

## ⚙️ Initial Server Configuration Walkthrough

Once the bot joins your server, an Administrator can run:
1. `/config welcome channel:#welcome message:Welcome to {server}, {user}!`
2. `/config modlog channel:#mod-logs`
3. `/config serverlog channel:#server-logs`
4. `/config tickets category:Support Tickets`
5. `/ticket panel` in your support channel to deploy the ticket launcher.
6. `/selfrole add role:@Gamers label:Gamers emoji:🎮` and `/selfrole panel` to post a role selector.
