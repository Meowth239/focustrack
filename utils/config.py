import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# User settings
DEFAULT_MORNING_HOUR = int(os.getenv("DEFAULT_MORNING_HOUR", 8))
DEFAULT_MORNING_MINUTE = int(os.getenv("DEFAULT_MORNING_MINUTE", 0))
NUDGE_INTERVAL_HOURS = int(os.getenv("NUDGE_INTERVAL_HOURS", 3))
GRACE_DAYS = int(os.getenv("GRACE_DAYS", 1))

# Points
POINTS_RUN = int(os.getenv("POINTS_RUN", 10))
POINTS_GYM = int(os.getenv("POINTS_GYM", 10))
POINTS_STUDY_PER_HOUR = int(os.getenv("POINTS_STUDY_PER_HOUR", 5))

# Streaks
STREAK_BRONZE = int(os.getenv("STREAK_BRONZE", 7))
STREAK_SILVER = int(os.getenv("STREAK_SILVER", 30))
STREAK_GOLD = int(os.getenv("STREAK_GOLD", 90))

# Paths
DB_PATH = os.getenv("DB_PATH", "focustrack.db")