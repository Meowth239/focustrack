# FocusTrack Bot

A Telegram bot for tracking fitness, study sessions, and weight progress.

## Features

- **Exercise Tracking** — Log runs and gym sessions
- **Study Tracking** — Track study time by subject (R, quant, etc.)
- **Weight Logging** — Track weight and progress toward goal
- **Points & Levels** — Earn points for activities, level up
- **Daily Goals** — Set daily focus with `/intent`
- **Weekly Review** — Summary of your week's progress

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/run [km]` | Log a run (e.g., `/run 5`) |
| `/gym [mins]` | Log gym session (e.g., `/gym 45`) |
| `/study [subject] [mins]` | Log study (e.g., `/study r 30`) |
| `/weight [kg]` | Log weight (e.g., `/weight 92.5`) |
| `/stats` | View your progress |
| `/intent [study], [exercise]` | Set today's focus |
| `/whatnow` | Get a suggestion |
| `/weekly` | Weekly summary |

## Setup

1. **Create a bot** — Message @BotFather on Telegram
2. **Get your bot token** — Copy the token from @BotFather
3. **Deploy with Docker:**

```bash
# Clone the repo
git clone https://github.com/yourusername/focustrack.git
cd focustrack

# Edit .env with your bot token
cp .env.example .env
nano .env  # Replace BOT_TOKEN with your token

# Build and run
docker-compose up -d --build
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | (required) | Telegram bot token |
| `POINTS_RUN` | 10 | Points per run |
| `POINTS_GYM` | 10 | Points per gym session |
| `POINTS_STUDY_PER_HOUR` | 5 | Points per hour of study |
| `STREAK_BRONZE` | 7 | Days for bronze streak |
| `STREAK_SILVER` | 30 | Days for silver streak |
| `STREAK_GOLD` | 90 | Days for gold streak |

## Tech Stack

- Python 3.11
- python-telegram-bot
- SQLAlchemy (SQLite)
- Docker

## License

MIT